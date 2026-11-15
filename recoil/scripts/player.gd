extends CharacterBody3D

const BULLET_SCENE := preload("res://scenes/bullet.tscn")
const SHOT_SOUND := preload("res://sounds/gun/pistol-sound-effect_zejYI9w.mp3")
const GUN_SHELL := Color(0.86, 0.06, 0.09)
const GUN_METAL := Color(1.0, 0.76, 0.2)

@export var walk_speed := 1.0
@export var sprint_speed := 2.0
@export var jump_speed := 3.3
@export var mouse_sensitivity := 0.0022
@export var scope_fov := 50.0
@export var scope_speed := 12.0
@export var scope_sensitivity := 0.6
@export var health_max := 100.0
@export var hunger_max := 100.0
@export var hunger_sprint_drain := 15.0
@export var hunger_regen := 10.0
@export var hunger_slide_jump_cost := 30.0
@export var starve_damage := 2.5
@export var damage := 34.0
@export var bullet_speed := 20.0
@export var fire_rate := 0.12
@export var bounce_restitution := 0.66
@export var bounce_threshold := 1.6
@export var canister_size := 10
@export var pickup_radius := 0.45
@export var slide_time := 0.55
@export var slide_speed := 3.1
@export var roll_time := 0.42
@export var roll_speed := 3.8
@export var stamina_max := 100.0
@export var sprint_drain := 15.0
@export var slide_jump_cost := 30.0
@export var stamina_regen := 10.0
@export var sprint_min := 30.0
@export var stand_height := 1.8
@export var crouch_height := 0.9
@export var stand_head := 1.62
@export var crouch_head := 0.82

@export_group("Motion")
@export var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)
@export var acceleration := 40.0
@export var pitch_limit := 1.45

@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var muzzle: Marker3D = $Head/Camera3D/Muzzle
@onready var gun: Node3D = $Head/Camera3D/Gun
@onready var collider: CollisionShape3D = $Collision

var pitch := 0.0
var cooldown := 0.0
var ammo := 0
var camera_rest := Vector3.ZERO
var dip_tween: Tween
var head_tween: Tween
var spin_tween: Tween
var shells: Array[MeshInstance3D] = []
var slide_timer := 0.0
var roll_timer := 0.0
var slide_dir := Vector3.FORWARD
var roll_dir := Vector3.RIGHT
var slide_jump := false
var stamina := 0.0
var exhausted := false
var low := false
var stand_shape: Shape3D
var crouch_shape: Shape3D
var fov_default := 80.0
var aiming := false
var health := 0.0
var hunger := 0.0
var gun_rest := Vector3.ZERO
var gun_aim := Vector3.ZERO
var shot_players: Array[AudioStreamPlayer] = []
var shot_index := 0

func _ready() -> void:
	add_to_group("player")
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	camera_rest = camera.position
	stand_shape = collider.shape
	crouch_shape = (stand_shape as CapsuleShape3D).duplicate()
	(crouch_shape as CapsuleShape3D).height = crouch_height
	fov_default = camera.fov
	gun_rest = gun.position
	gun_aim = Vector3(gun_rest.x * 0.38, gun_rest.y + 0.035, gun_rest.z)
	ammo = canister_size
	stamina = stamina_max
	health = health_max
	hunger = hunger_max
	paint_gun()
	build_canister()
	update_canister()
	build_shot_players()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var sensitivity := mouse_sensitivity * (scope_sensitivity if aiming else 1.0)
		rotate_y(-event.relative.x * sensitivity)
		pitch = clampf(pitch - event.relative.y * sensitivity, -pitch_limit, pitch_limit)
		head.rotation.x = pitch
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed:
		if Input.mouse_mode == Input.MOUSE_MODE_VISIBLE:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _physics_process(delta: float) -> void:
	var grounded := is_on_floor()
	if stamina <= 0.0:
		exhausted = true
	elif exhausted and stamina >= sprint_min:
		exhausted = false
	var sprinting := Input.is_action_pressed("sprint") and not exhausted
	var falling := velocity.y
	if not grounded:
		velocity.y -= gravity * delta
	if Input.is_action_just_pressed("jump") and grounded:
		var sliding := slide_timer > 0.0
		velocity.y = jump_speed
		cancel_low()
		if sliding and stamina > 0.0:
			slide_jump = true
			stamina = maxf(stamina - slide_jump_cost, 0.0)
			hunger = maxf(hunger - hunger_slide_jump_cost, 0.0)
			velocity.x = slide_dir.x * slide_speed * 2.0
			velocity.z = slide_dir.z * slide_speed * 2.0
	if Input.is_action_just_pressed("slide") and sprinting:
		start_slide(grounded)
	if Input.is_action_just_pressed("roll") and Input.is_action_pressed("sprint"):
		start_roll(grounded)

	if slide_timer > 0.0:
		slide_timer = maxf(slide_timer - delta, 0.0)
		velocity.x = slide_dir.x * slide_speed
		velocity.z = slide_dir.z * slide_speed
		if slide_timer <= 0.0:
			stand()
	elif roll_timer > 0.0:
		roll_timer = maxf(roll_timer - delta, 0.0)
		velocity.x = roll_dir.x * roll_speed
		velocity.z = roll_dir.z * roll_speed
		if roll_timer <= 0.0:
			stand()
	else:
		if low:
			stand()
		if grounded and velocity.y <= 0.0:
			slide_jump = false
		if not slide_jump:
			var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
			var direction := (transform.basis * Vector3(input.x, 0.0, input.y)).normalized()
			var speed := sprint_speed if sprinting else walk_speed
			velocity.x = move_toward(velocity.x, direction.x * speed, acceleration * delta)
			velocity.z = move_toward(velocity.z, direction.z * speed, acceleration * delta)

	if sprinting and grounded and not low:
		stamina = maxf(stamina - sprint_drain * delta, 0.0)
	elif not low:
		stamina = minf(stamina + stamina_regen * delta, stamina_max)

	if sprinting and grounded and not low:
		hunger = maxf(hunger - hunger_sprint_drain * delta, 0.0)
	elif not low:
		hunger = minf(hunger + hunger_regen * delta, hunger_max)
	if hunger <= 0.0:
		take_hit(starve_damage * delta)

	move_and_slide()

	if not grounded and is_on_floor() and falling < -bounce_threshold:
		land(falling)
	collect_shells()

func start_slide(grounded: bool) -> void:
	if not grounded or slide_timer > 0.0 or roll_timer > 0.0:
		return
	var flat := Vector3(velocity.x, 0.0, velocity.z)
	if flat.length() < 0.1:
		flat = -global_basis.z
	slide_dir = flat.normalized()
	slide_timer = slide_time
	drop()

func start_roll(grounded: bool) -> void:
	if not grounded or slide_timer > 0.0 or roll_timer > 0.0:
		return
	var side := 1.0
	if Input.is_action_pressed("move_left"):
		side = -1.0
	elif Input.is_action_pressed("move_right"):
		side = 1.0
	roll_dir = Vector3(global_basis.x.x, 0.0, global_basis.x.z).normalized() * side
	roll_timer = roll_time
	drop()
	dip(0.6)
	spin(side)

func drop() -> void:
	if low:
		return
	low = true
	collider.shape = crouch_shape
	collider.position.y = crouch_height * 0.5
	swing_head(crouch_head)

func stand() -> void:
	if not low:
		return
	if test_move(global_transform, Vector3.UP * (stand_height - crouch_height) * scale.y):
		return
	low = false
	collider.shape = stand_shape
	collider.position.y = stand_height * 0.5
	swing_head(stand_head)

func cancel_low() -> void:
	slide_timer = 0.0
	roll_timer = 0.0
	if spin_tween != null:
		spin_tween.kill()
	camera.rotation.z = 0.0
	stand()

func swing_head(height: float) -> void:
	if head_tween != null:
		head_tween.kill()
	head_tween = create_tween()
	head_tween.tween_property(head, "position:y", height, 0.1)

func spin(side: float) -> void:
	if spin_tween != null:
		spin_tween.kill()
	camera.rotation.z = 0.0
	spin_tween = create_tween()
	spin_tween.tween_property(camera, "rotation:z", -TAU * side, roll_time)
	spin_tween.tween_callback(reset_spin)

func reset_spin() -> void:
	camera.rotation.z = 0.0

func land(falling: float) -> void:
	var rise := minf(-falling * bounce_restitution, jump_speed)
	if rise < 0.6:
		return
	velocity.y = rise
	var strength := clampf(rise / (jump_speed * 1.5), 0.15, 1.0)
	dip(strength)
	var scene := get_tree().current_scene
	if scene != null and scene.has_method("warp"):
		scene.warp(global_position, strength * 0.8)

func collect_shells() -> void:
	if ammo >= canister_size:
		return
	for node in get_tree().get_nodes_in_group("shell"):
		var offset := (node as Node3D).global_position - global_position
		if Vector2(offset.x, offset.z).length() > pickup_radius:
			continue
		if absf(offset.y) > 1.0:
			continue
		if not pickable_shell(node):
			continue
		(node as Node3D).collect()
		ammo += 1
		update_canister()
		if ammo >= canister_size:
			return

func pickable_shell(node: Node) -> bool:
	if node.has_method("is_pickable"):
		return node.is_pickable()
	return true

func paint_gun() -> void:
	for node in gun.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance.mesh == null:
			continue
		for surface in mesh_instance.mesh.get_surface_count():
			var source := mesh_instance.get_surface_override_material(surface)
			if source == null:
				source = mesh_instance.mesh.surface_get_material(surface)
			var material := source as StandardMaterial3D
			if material == null or material.resource_name == "Material.004":
				continue
			var painted := material.duplicate() as StandardMaterial3D
			painted.albedo_texture = null
			painted.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED
			if material.resource_name == "FlatParts":
				painted.albedo_color = GUN_SHELL
				painted.metallic = 0.3
				painted.roughness = 0.3
				painted.emission_enabled = true
				painted.emission = GUN_SHELL
				painted.emission_energy_multiplier = 0.45
			else:
				painted.albedo_color = GUN_METAL
				painted.metallic = 0.7
				painted.roughness = 0.25
				painted.emission_enabled = true
				painted.emission = GUN_METAL
				painted.emission_energy_multiplier = 0.15
			mesh_instance.set_surface_override_material(surface, painted)

func build_canister() -> void:
	var bottle := gun.find_child("defaultMaterial8", true, false) as MeshInstance3D
	if bottle == null:
		return
	var bottle_frame := gun.global_transform.affine_inverse() * bottle.global_transform
	var box: AABB = bottle_frame * bottle.get_aabb()
	if box.size.x <= 0.0:
		return
	var holder := Node3D.new()
	holder.name = "Canister"
	gun.add_child(holder)
	var length := box.size.x
	var radius := box.size.y * 0.11
	var step := length * 0.86 / maxf(float(canister_size - 1), 1.0)
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.98, 0.74, 0.16)
	material.metallic = 0.65
	material.roughness = 0.28
	for i in canister_size:
		var mesh := CylinderMesh.new()
		mesh.height = length * 0.075
		mesh.top_radius = radius
		mesh.bottom_radius = radius
		mesh.radial_segments = 10
		mesh.rings = 1
		var shell := MeshInstance3D.new()
		shell.mesh = mesh
		shell.material_override = material
		shell.rotation = Vector3(0.0, 0.0, PI * 0.5)
		shell.position = Vector3(
			box.position.x + length * 0.07 + step * i,
			box.get_center().y - box.size.y * 0.08,
			box.get_center().z)
		holder.add_child(shell)
		shells.append(shell)

func build_shot_players() -> void:
	for i in 4:
		var source := AudioStreamPlayer.new()
		source.name = "Shot%d" % i
		source.stream = SHOT_SOUND
		source.volume_db = -3.0
		add_child(source)
		shot_players.append(source)

func play_shot() -> void:
	if shot_players.is_empty():
		return
	shot_players[shot_index].play()
	shot_index = (shot_index + 1) % shot_players.size()

func update_canister() -> void:
	for i in shells.size():
		shells[i].visible = i < ammo

func feed(amount: float) -> void:
	hunger = minf(hunger + amount, hunger_max)

func heal(amount: float) -> void:
	health = minf(health + amount, health_max)

func clear_bullets(include_resting := false) -> void:
	var scene := get_tree().current_scene
	if scene != null and scene.has_method("clear_shooter_bullets"):
		scene.clear_shooter_bullets(self, include_resting)

func take_hit(amount: float, _headshot := false) -> void:
	health = maxf(health - amount, 0.0)
	if health > 0.0:
		return
	clear_bullets(true)
	var scene := get_tree().current_scene
	if scene != null and scene.has_method("on_player_died") and not scene.on_player_died():
		return
	ammo = canister_size
	update_canister()
	health = health_max
	hunger = hunger_max
	if scene != null and scene.has_method("pick_spawn"):
		global_position = scene.pick_spawn(self).origin
		velocity = Vector3.ZERO
		slide_timer = 0.0
		roll_timer = 0.0

func dip(strength: float) -> void:
	if dip_tween != null:
		dip_tween.kill()
	dip_tween = create_tween()
	dip_tween.tween_property(camera, "position", camera_rest - Vector3(0.0, 0.1 * strength, 0.0), 0.06)
	dip_tween.tween_property(camera, "position", camera_rest, 0.24)

func _process(delta: float) -> void:
	cooldown = maxf(cooldown - delta, 0.0)
	aiming = Input.is_action_pressed("aim") and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and not low
	var target_fov := scope_fov if aiming else fov_default
	camera.fov = lerpf(camera.fov, target_fov, clampf(delta * scope_speed, 0.0, 1.0))
	var gun_target := gun_aim if aiming else gun_rest
	gun.position = gun.position.lerp(gun_target, clampf(delta * scope_speed, 0.0, 1.0))
	if Input.is_action_just_pressed("shoot") and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		shoot()

func shoot() -> void:
	if cooldown > 0.0 or ammo <= 0:
		return
	cooldown = fire_rate
	ammo -= 1
	update_canister()
	play_shot()

	var forward := -camera.global_basis.z
	var muzzle_position := muzzle.global_position
	var aim_point := camera.global_position + forward * 250.0

	var aim_query := PhysicsRayQueryParameters3D.create(camera.global_position, aim_point, 1 | 2)
	aim_query.collide_with_areas = true
	aim_query.exclude = [get_rid()]
	var aim_result := get_world_3d().direct_space_state.intersect_ray(aim_query)
	if not aim_result.is_empty():
		aim_point = aim_result.position

	var aim_direction := (aim_point - muzzle_position).normalized()
	if aim_direction.length_squared() < 0.000001:
		aim_direction = forward

	var bullet := BULLET_SCENE.instantiate()
	bullet.direction = aim_direction
	bullet.damage = damage
	bullet.speed = bullet_speed
	bullet.shooter_rid = get_rid()
	bullet.shooter = self
	get_parent().add_child(bullet)
	bullet.global_position = muzzle_position

	pitch = clampf(pitch + randf_range(0.008, 0.018), -1.45, 1.45)
	head.rotation.x = pitch
