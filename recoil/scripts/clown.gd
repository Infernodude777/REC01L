extends CharacterBody3D

signal died

const POOF_SCENE := preload("res://scenes/poof.tscn")
const PATHFIND_SCRIPT := preload("res://scripts/pathfind.gd")

@export var max_health := 100.0
@export var respawn_delay := 2.5
@export var headshot_multiplier := 2.0
@export var chase_speed := 2.4
@export var speed_spread := 0.6
@export var punch_damage := 5.0
@export var punch_reach := 0.72
@export var punch_windup := 0.33
@export var punch_recover := 0.5
@export var min_punch_interval := 0.7
@export var max_punch_interval := 1.7
@export var jump_speed := 5.4
@export var gravity := 22.0
@export var turn_speed := 10.0
@export var acceleration := 30.0
@export var duck_speed_scale := 0.55
@export var slide_speed := 3.4
@export var slide_time := 0.45
@export var slide_cooldown := 2.0
@export var slide_slope := 28.0

@export_group("Stance")
@export var duck_pitch := 52.0
@export var slide_pitch := 76.0
@export var slide_lift := 0.11
@export var slide_center := 0.24

@export_group("Pathfinding")
@export var repath_interval := 0.3
@export var retreat_time := 0.55
@export var retreat_speed_scale := 1.5
@export var flank_interval_min := 4.0
@export var flank_interval_max := 8.0

@export_group("Size")
@export_range(0.0, 0.4, 0.01) var size_spread := 0.12

@export_group("Bounce")
@export var bounce_restitution := 0.35
@export var bounce_threshold := 1.6
@export var bob_height := 0.03
@export var bob_speed := 9.0

var health := 100.0
var alive := true
var nav_ready := false

var anim_player: AnimationPlayer
var model: Node3D
var model_scale := Vector3.ONE
var model_home_position := Vector3.ZERO
var model_home_rotation := Vector3.ZERO
var flinch_tween: Tween
var laugh_tween: Tween
var home: Transform3D
var agent: NavigationAgent3D
var player: Node3D
var pathfinder

var move_speed := 2.4
var punch_speed := 1.0
var attack_timer := 0.0
var punch_timer := 0.0
var punch_hit := false
var retreat_pending := false
var hop_timer := 0.0
var climb_timer := 0.0
var climb_time := 0.0
var climb_grace := 0.0
var climb_stop_y := 0.0
var climbing := false
var current_animation := ""

var body_shape: CollisionShape3D
var stand_shape: Shape3D
var crouch_shape: CapsuleShape3D
var stand_height := 0.59
var crouch_height := 0.33
var stance_lift := 0.0
var bob_phase := 0.0
var fall_speed := 0.0
var ducked := false
var slide_timer := 0.0
var slide_cooldown_timer := 0.0
var slide_dir := Vector3.FORWARD

func _ready() -> void:
	add_to_group("clown")
	health = max_health
	home = global_transform
	floor_max_angle = deg_to_rad(50.0)
	floor_snap_length = 0.4
	for node in find_children("*", "AnimationPlayer", true, false):
		anim_player = node as AnimationPlayer
		break
	var size_scale := 1.0 + randf_range(-size_spread, size_spread)
	model = get_node_or_null("clown") as Node3D
	if model != null:
		model_scale = model.scale * size_scale
		model.scale = model_scale
		model_home_position = model.position
		model_home_rotation = model.rotation
	agent = get_node_or_null("NavigationAgent3D") as NavigationAgent3D
	body_shape = get_node_or_null("Body") as CollisionShape3D
	if body_shape != null:
		var capsule := body_shape.shape as CapsuleShape3D
		if capsule != null:
			stand_shape = capsule.duplicate()
			(stand_shape as CapsuleShape3D).height = capsule.height * size_scale
			stand_height = (stand_shape as CapsuleShape3D).height
			crouch_height = maxf(stand_height * 0.55, 0.2)
			crouch_shape = capsule.duplicate() as CapsuleShape3D
			crouch_shape.height = crouch_height
			body_shape.shape = stand_shape
			body_shape.position.y = stand_height * 0.5
	for area_name in ["Hurtbox", "HeadHurtbox"]:
		var area := get_node_or_null(area_name) as Node3D
		if area != null:
			area.scale = Vector3.ONE * size_scale
	move_speed = maxf(0.8, chase_speed + randf_range(-speed_spread, speed_spread))
	punch_speed = randf_range(1.0, 1.6)
	attack_timer = randf_range(0.4, 1.0)
	player = get_tree().get_first_node_in_group("player")
	pathfinder = PATHFIND_SCRIPT.new()
	pathfinder.setup(self, agent)
	if player != null:
		pathfinder.set_player(player)
	loop_animations()
	play_animation("Idle")

func loop_animations() -> void:
	if anim_player == null:
		return
	for animation_name in ["Idle", "Walk", "Run"]:
		if anim_player.has_animation(animation_name):
			anim_player.get_animation(animation_name).loop_mode = Animation.LOOP_LINEAR

func _physics_process(delta: float) -> void:
	if not alive:
		return
	fall_speed = velocity.y
	if player == null or not is_instance_valid(player):
		player = get_tree().get_first_node_in_group("player")
		if player == null:
			apply_gravity(delta)
			move_and_slide()
			return
	if pathfinder == null:
		pathfinder = PATHFIND_SCRIPT.new()
		pathfinder.setup(self, agent)
	pathfinder.set_player(player)

	hop_timer = maxf(hop_timer - delta, 0.0)
	attack_timer = maxf(attack_timer - delta, 0.0)
	climb_grace = maxf(climb_grace - delta, 0.0)
	slide_cooldown_timer = maxf(slide_cooldown_timer - delta, 0.0)

	if punch_timer > 0.0:
		swing(delta)
		return

	var to_player := player.global_position - global_position
	var flat := Vector3(to_player.x, 0.0, to_player.z)
	var distance := flat.length()
	var plan: Dictionary = pathfinder.think(delta, to_player, distance)
	var direction: Vector3 = plan.direction
	if direction.length_squared() < 0.0001:
		direction = flat.normalized()
	else:
		direction = direction.normalized()
	var retreating := bool(plan.retreat)

	if retreating:
		face_towards(direction, delta)
	elif distance > 0.05:
		face_towards(flat, delta)

	if not retreating and not ducked and distance <= punch_reach and attack_timer <= 0.0 and absf(to_player.y) < 0.7:
		begin_punch()
		return

	if retreating:
		var escape := move_speed * retreat_speed_scale
		velocity.x = move_toward(velocity.x, direction.x * escape, acceleration * delta)
		velocity.z = move_toward(velocity.z, direction.z * escape, acceleration * delta)
		if is_on_floor() and hop_timer <= 0.0 and pathfinder.wall_ahead(direction):
			velocity.y = jump_speed
			hop_timer = 0.6
		apply_gravity(delta)
		move_and_slide()
		check_bounce()
		update_animation()
		return

	var height_gap := player.global_position.y - global_position.y
	if climbing:
		climb_time += delta
		velocity.x = direction.x * 1.2
		velocity.z = direction.z * 1.2
		velocity.y = 2.2
		move_and_slide()
		var lost_wall: bool = climb_time > 0.45 and not is_on_wall() and not pathfinder.wall_ahead(direction)
		var reached := climb_stop_y > 0.0 and global_position.y >= climb_stop_y - 0.02
		if reached or lost_wall or climb_time > 2.2:
			climbing = false
			climb_time = 0.0
			climb_stop_y = 0.0
			climb_grace = 0.8
			velocity.y = maxf(velocity.y, 1.2)
		update_animation()
		return

	var wall_close: bool = is_on_wall() or pathfinder.wall_ahead(direction)
	if not ducked and climb_grace <= 0.0 and (height_gap > stand_height * 0.8 or bool(plan.climb)) and distance < stand_height * 10.0 and wall_close:
		climb_timer += delta
		if climb_timer > 0.22:
			climbing = true
			climb_time = 0.0
			climb_timer = 0.0
			if bool(plan.climb) and float(plan.ledge_top) > 0.01:
				climb_stop_y = global_position.y + float(plan.ledge_top) + 0.05
			else:
				climb_stop_y = player.global_position.y + 0.1
			velocity.y = 2.2
			move_and_slide()
			update_animation()
			return
	else:
		climb_timer = maxf(climb_timer - delta, 0.0)

	var low_ahead: bool = pathfinder.duck_ahead(direction)
	if ducked and slide_timer <= 0.0 and can_stand() and not low_ahead:
		end_duck()
	if not ducked and not climbing and is_on_floor() and slide_cooldown_timer <= 0.0:
		if low_ahead or bool(plan.duck):
			if distance > 1.4:
				start_slide(direction)
			else:
				begin_duck()
		elif distance > 1.5:
			var normal := get_floor_normal()
			var slope_angle := rad_to_deg(acos(clampf(normal.dot(Vector3.UP), -1.0, 1.0)))
			if slope_angle > slide_slope:
				var downhill := Vector3(normal.x, 0.0, normal.z)
				if downhill.length_squared() > 0.01 and direction.dot(downhill.normalized()) > 0.35:
					start_slide(direction)

	if slide_timer > 0.0:
		slide_timer = maxf(slide_timer - delta, 0.0)
		velocity.x = slide_dir.x * slide_speed
		velocity.z = slide_dir.z * slide_speed
		if slide_timer <= 0.0 and can_stand() and not low_ahead:
			end_duck()
	else:
		var speed := move_speed * (duck_speed_scale if ducked else 1.0)
		var desired := direction * speed
		velocity.x = move_toward(velocity.x, desired.x, acceleration * delta)
		velocity.z = move_toward(velocity.z, desired.z, acceleration * delta)

	if not ducked and is_on_floor() and hop_timer <= 0.0 and bool(plan.jump) and not bool(plan.climb):
		velocity.y = jump_speed
		hop_timer = 0.6

	apply_gravity(delta)
	move_and_slide()
	check_bounce()
	pathfinder.track_stuck(delta, direction, distance)
	update_animation()

func begin_duck() -> void:
	if ducked:
		return
	stop_laugh()
	ducked = true
	if body_shape != null and crouch_shape != null:
		body_shape.shape = crouch_shape
		body_shape.position.y = crouch_height * 0.5
	apply_stance_pose(slide_timer > 0.0)

func end_duck() -> void:
	if not ducked:
		return
	if not can_stand():
		return
	stop_laugh()
	ducked = false
	if body_shape != null and stand_shape != null:
		body_shape.shape = stand_shape
		body_shape.position.y = stand_height * 0.5
	clear_stance_pose()

func can_stand() -> bool:
	if not ducked:
		return true
	if body_shape == null:
		return true
	return not test_move(global_transform, Vector3.UP * (stand_height - crouch_height))

func start_slide(direction: Vector3) -> void:
	if slide_cooldown_timer > 0.0 or not is_on_floor():
		return
	if direction.length_squared() < 0.01:
		direction = -global_basis.z
	slide_dir = direction.normalized()
	slide_timer = slide_time
	slide_cooldown_timer = slide_cooldown
	begin_duck()
	apply_stance_pose(true)

func apply_stance_pose(sliding: bool) -> void:
	if model == null:
		return
	var pitch := slide_pitch if sliding else duck_pitch
	var lift := slide_lift if sliding else slide_lift * 0.7
	var shift := slide_center if sliding else slide_center * 0.7
	model.scale = model_scale
	model.rotation = Vector3(deg_to_rad(-pitch), model_home_rotation.y, model_home_rotation.z)
	stance_lift = lift
	model.position = model_home_position + Vector3(0.0, stance_lift, shift)

func clear_stance_pose() -> void:
	if model == null:
		return
	stance_lift = 0.0
	model.scale = model_scale
	model.rotation = model_home_rotation
	model.position = model_home_position

func reset_stance() -> void:
	stop_laugh()
	ducked = false
	slide_timer = 0.0
	if body_shape != null and stand_shape != null:
		body_shape.shape = stand_shape
		body_shape.position.y = stand_height * 0.5
	clear_stance_pose()

func swing(delta: float) -> void:
	punch_timer = maxf(punch_timer - delta, 0.0)
	velocity.x = move_toward(velocity.x, 0.0, acceleration * delta)
	velocity.z = move_toward(velocity.z, 0.0, acceleration * delta)
	if not punch_hit and punch_timer <= punch_recover:
		punch_hit = true
		if in_punch_range() and player.has_method("take_hit"):
			player.take_hit(punch_damage)
			retreat_pending = true
			attack_timer = maxf(attack_timer, 0.8)
			var scene := get_tree().current_scene
			if scene != null and scene.has_method("clown_laugh"):
				scene.clown_laugh(global_position, self)
	if punch_timer <= 0.0:
		attack_timer = randf_range(min_punch_interval, max_punch_interval)
		current_animation = ""
		if retreat_pending:
			retreat_pending = false
			if pathfinder != null:
				pathfinder.start_retreat()
	apply_gravity(delta)
	move_and_slide()
	check_bounce()
	update_animation()

func begin_punch() -> void:
	punch_timer = punch_windup + punch_recover
	punch_hit = false
	velocity.x = 0.0
	velocity.z = 0.0
	current_animation = "Punch"
	if anim_player != null and anim_player.has_animation("Punch"):
		anim_player.speed_scale = punch_speed
		anim_player.play("Punch", 0.05)

func in_punch_range() -> bool:
	if player == null or not is_instance_valid(player):
		return false
	var offset := player.global_position - global_position
	return Vector2(offset.x, offset.z).length() <= punch_reach and absf(offset.y) < 0.7

func face_towards(direction: Vector3, delta: float) -> void:
	if direction.length_squared() < 0.001:
		return
	var yaw := atan2(direction.x, direction.z)
	rotation.y = lerp_angle(rotation.y, yaw, clampf(turn_speed * delta, 0.0, 1.0))

func laugh() -> void:
	if model == null:
		return
	if laugh_tween != null:
		laugh_tween.kill()
	var base_scale := model.scale
	var base_rotation := model.rotation
	laugh_tween = create_tween()
	for i in 3:
		var tilt := 0.12 if i % 2 == 0 else -0.12
		laugh_tween.tween_property(model, "scale", base_scale * Vector3(1.08, 0.9, 1.08), 0.06)
		laugh_tween.tween_property(model, "rotation:z", tilt, 0.06)
		laugh_tween.tween_property(model, "scale", base_scale, 0.07)
		laugh_tween.tween_property(model, "rotation:z", 0.0, 0.07)
	laugh_tween.tween_callback(func(): model.rotation = base_rotation)

func stop_laugh() -> void:
	if laugh_tween != null:
		laugh_tween.kill()
		laugh_tween = null
	if model != null:
		model.rotation.z = 0.0

func apply_gravity(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	elif velocity.y < 0.0:
		velocity.y = -0.5

func check_bounce() -> void:
	if ducked or fall_speed > -bounce_threshold or not is_on_floor():
		return
	velocity.y = -fall_speed * bounce_restitution

func update_bob(horizontal: float) -> void:
	if model == null:
		return
	var pace := clampf(horizontal / maxf(move_speed, 0.1), 0.0, 1.2)
	bob_phase += get_physics_process_delta_time() * bob_speed * (0.4 + pace)
	if ducked:
		return
	model.position.y = model_home_position.y + stance_lift + absf(sin(bob_phase)) * bob_height * pace

func update_animation() -> void:
	var horizontal := Vector2(velocity.x, velocity.z).length()
	update_bob(horizontal)
	if punch_timer > 0.0:
		return
	if horizontal < 0.25:
		play_animation("Idle")
	elif horizontal > 1.9:
		play_animation("Run")
	else:
		play_animation("Walk")

func play_animation(animation_name: String, blend := 0.18) -> void:
	if anim_player == null or not anim_player.has_animation(animation_name):
		return
	if current_animation == animation_name:
		if not anim_player.is_playing():
			anim_player.play(animation_name, blend)
		return
	current_animation = animation_name
	anim_player.play(animation_name, blend)
	var horizontal := Vector2(velocity.x, velocity.z).length()
	if animation_name == "Walk":
		anim_player.speed_scale = clampf(horizontal / 1.4, 0.85, 1.6)
	elif animation_name == "Run":
		anim_player.speed_scale = clampf(horizontal / 2.8, 0.85, 1.5)
	elif animation_name != "Punch":
		anim_player.speed_scale = 1.0

func take_hit(amount: float, headshot := false) -> void:
	if not alive:
		return
	health -= amount * (headshot_multiplier if headshot else 1.0)
	flinch()
	if health <= 0.0:
		die()

func flinch() -> void:
	if model == null:
		return
	stop_laugh()
	if flinch_tween != null:
		flinch_tween.kill()
	model.scale = model_scale * Vector3(1.06, 0.95, 1.06)
	flinch_tween = create_tween()
	flinch_tween.tween_property(model, "scale", model_scale, 0.16)

func die() -> void:
	if not alive:
		return
	alive = false
	punch_timer = 0.0
	retreat_pending = false
	velocity = Vector3.ZERO
	reset_stance()
	if pathfinder != null:
		pathfinder.reset()
	if agent != null:
		agent.target_position = global_position
	set_hurt_layers(false)
	var scene := get_tree().current_scene
	if scene != null and scene.has_method("clear_shooter_bullets"):
		scene.clear_shooter_bullets(self)
	died.emit()
	play_animation("Die", 0.08)
	burst()
	await get_tree().create_timer(1.1).timeout
	if model != null:
		model.visible = false
	await get_tree().create_timer(respawn_delay).timeout
	move_to_spawn()
	if model != null:
		model.visible = true
	burst()
	health = max_health
	alive = true
	current_animation = ""
	attack_timer = randf_range(0.5, 1.2)
	punch_speed = randf_range(1.0, 1.6)
	set_hurt_layers(true)
	play_animation("Idle")
	if nav_ready and agent != null and player != null:
		agent.target_position = player.global_position

func move_to_spawn() -> void:
	reset_stance()
	var scene := get_tree().current_scene
	if scene != null and scene.has_method("pick_spawn"):
		global_transform = scene.pick_spawn(self)
	else:
		transform = home
	velocity = Vector3.ZERO
	if pathfinder != null:
		pathfinder.reset()

func set_hurt_layers(enabled: bool) -> void:
	collision_layer = 4 if enabled else 0
	var hurtbox := get_node_or_null("Hurtbox") as Area3D
	if hurtbox != null:
		hurtbox.collision_layer = 2 if enabled else 0
	var head_hurtbox := get_node_or_null("HeadHurtbox") as Area3D
	if head_hurtbox != null:
		head_hurtbox.collision_layer = 2 if enabled else 0

func burst() -> void:
	var parent := get_tree().current_scene
	if parent == null:
		return
	var poof := POOF_SCENE.instantiate()
	parent.add_child(poof)
	poof.global_position = global_position + Vector3(0.0, 0.1, 0.0)
