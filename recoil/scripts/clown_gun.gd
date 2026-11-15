extends "res://scripts/clown.gd"

const BULLET_SCENE := preload("res://scenes/bullet.tscn")
const GUN_SCENE := preload("res://scenes/gun.tscn")
const SHOT_SOUND := preload("res://sounds/gun/pistol-sound-effect_zejYI9w.mp3")

@export_group("Gun")
@export var hold_pose := "Aim"
@export var hold_blend := 0.2
@export var gun_length := 0.26
@export var shell_color := Color(0.92, 0.09, 0.12)
@export var metal_color := Color(1.0, 0.92, 0.55)
@export var accent_color := Color(0.16, 0.62, 0.3)

@export_group("Shooting")
@export var bullet_color := Color(0.93, 0.05, 0.08)
@export var bullet_damage := 20.0
@export var bullet_speed := 18.0
@export var bullet_gravity := 16.0
@export var burst_size := 3
@export var burst_gap := 0.16
@export var burst_cooldown := 3.0
@export var aim_spread := 1.0
@export var blind_spread := 9.0
@export var blind_lift := 20.0
@export var sight_range := 26.0
@export var lead_factor := 0.75

@export_group("Spacing")
@export var hold_distance := 5.0
@export var close_distance := 3.1
@export var sidestep_time_min := 1.4
@export var sidestep_time_max := 2.8

@export_group("Positioning")
@export var spot_samples := 18
@export var spot_max_distance := 8.5
@export var spot_recheck := 1.4
@export var spot_arrive := 0.45
@export var spot_separation := 3.0
@export var spot_drift := 0.45
@export var body_radius := 0.22

var gun_pivot: Node3D
var gun: Node3D
var muzzle: Marker3D
var fire_timer := 0.0
var burst_left := 0
var burst_gap_timer := 0.0
var sidestep_sign := 1.0
var sidestep_timer := 0.0
var blind_yaw := 0.0
var blind_pitch := 0.0
var sees_player := false
var spot := Vector3.ZERO
var spot_timer := 0.0
var spot_lost := 0.0
var spot_progress_timer := 0.0
var spot_progress_anchor := Vector3.ZERO
var shot_players: Array[AudioStreamPlayer3D] = []
var shot_index := 0
var body_probe: Shape3D

func _ready() -> void:
	super._ready()
	fire_timer = randf_range(0.6, 1.3)
	sidestep_sign = 1.0 if randf() < 0.5 else -1.0
	sidestep_timer = randf_range(sidestep_time_min, sidestep_time_max)
	setup_gun()
	play_animation(hold_pose, hold_blend)

func loop_animations() -> void:
	super.loop_animations()
	if anim_player != null and anim_player.has_animation(hold_pose):
		anim_player.get_animation(hold_pose).loop_mode = Animation.LOOP_LINEAR

func setup_gun() -> void:
	gun_pivot = get_node_or_null("clown/GunHold") as Node3D
	if gun_pivot == null:
		return
	gun = gun_pivot.get_node_or_null("Gun") as Node3D
	if gun == null:
		gun = GUN_SCENE.instantiate()
		gun.name = "Gun"
		gun_pivot.add_child(gun)
	fit_gun()
	paint_gun()
	build_muzzle()
	build_shot_players()

func fit_gun() -> void:
	var box := gun_box()
	if box.size.z <= 0.0001:
		return
	var length := box.size.z * gun_pivot.global_basis.get_scale().z
	if length <= 0.0001:
		return
	gun.scale = gun.scale * (gun_length / length)
	box = gun_box()
	gun.position.y -= box.get_center().y
	gun.position.x -= box.get_center().x
	gun.position.z -= box.position.z

func gun_box() -> AABB:
	var to_pivot := gun_pivot.global_transform.affine_inverse()
	var box := AABB()
	var first := true
	for node in gun.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance.mesh == null:
			continue
		var mesh_box: AABB = (to_pivot * mesh_instance.global_transform) * mesh_instance.get_aabb()
		box = mesh_box if first else box.merge(mesh_box)
		first = false
	return box

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
			if material == null:
				continue
			var painted := material.duplicate() as StandardMaterial3D
			match material.resource_name:
				"FlatParts":
					painted.albedo_texture = null
					painted.albedo_color = shell_color
					painted.emission_enabled = true
					painted.emission = shell_color
					painted.emission_energy_multiplier = 0.5
				"BotParts":
					painted.albedo_color = metal_color
				_:
					painted.albedo_texture = null
					painted.albedo_color = accent_color
					painted.emission_enabled = false
			painted.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED
			mesh_instance.set_surface_override_material(surface, painted)

func build_muzzle() -> void:
	if muzzle != null:
		return
	var box := gun_box()
	muzzle = Marker3D.new()
	muzzle.name = "Muzzle"
	muzzle.position = Vector3(0.0, 0.0, box.end.z)
	gun_pivot.add_child(muzzle)

func build_shot_players() -> void:
	if gun_pivot == null:
		return
	for i in 3:
		var source := AudioStreamPlayer3D.new()
		source.name = "Shot%d" % i
		source.stream = SHOT_SOUND
		source.volume_db = -2.0
		source.unit_size = 2.5
		source.max_distance = 26.0
		gun_pivot.add_child(source)
		shot_players.append(source)

func play_shot() -> void:
	if shot_players.is_empty():
		return
	shot_players[shot_index].play()
	shot_index = (shot_index + 1) % shot_players.size()

func _physics_process(delta: float) -> void:
	if not alive:
		burst_left = 0
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

	var to_player := player.global_position - global_position
	var flat := Vector3(to_player.x, 0.0, to_player.z)
	var distance := flat.length()
	var forward := flat / distance if distance > 0.001 else -global_basis.z

	face_towards(flat, delta)
	aim(delta, distance, to_player)
	shoot_cycle(delta)

	var desired := steer(delta, to_player, distance, forward)
	velocity.x = move_toward(velocity.x, desired.x * move_speed, acceleration * delta)
	velocity.z = move_toward(velocity.z, desired.z * move_speed, acceleration * delta)
	if is_on_floor() and hop_timer <= 0.0 and desired.length_squared() > 0.01 and pathfinder.wall_ahead(desired):
		velocity.y = jump_speed
		hop_timer = 0.7

	apply_gravity(delta)
	move_and_slide()
	check_bounce()
	pathfinder.track_stuck(delta, forward, distance)
	track_spot_progress(delta)
	update_animation()

func steer(delta: float, to_player: Vector3, distance: float, forward: Vector3) -> Vector3:
	update_spot(delta)
	if distance < close_distance:
		var escape := -forward
		if pathfinder != null and pathfinder.wall_ahead(escape):
			escape = Vector3(-forward.z, 0.0, forward.x) * sidestep_sign
		return escape.normalized() * 0.85
	var to_spot := spot - global_position
	to_spot.y = 0.0
	if to_spot.length() > spot_arrive:
		return path_direction(to_spot)
	return hold_spot(delta, to_spot, forward)

func track_spot_progress(delta: float) -> void:
	spot_progress_timer += delta
	if spot_progress_timer < 1.0:
		return
	var travelled := global_position.distance_to(spot_progress_anchor)
	spot_progress_anchor = global_position
	spot_progress_timer = 0.0
	var to_spot := spot - global_position
	to_spot.y = 0.0
	if to_spot.length() > spot_arrive and travelled < 0.2:
		spot = Vector3.ZERO
		spot_lost = 1.0

func update_spot(delta: float) -> void:
	spot_timer = maxf(spot_timer - delta, 0.0)
	if spot == Vector3.ZERO or not spot_valid():
		spot_lost += delta
	else:
		spot_lost = 0.0
	if spot == Vector3.ZERO or spot_timer <= 0.0 or spot_lost > 0.4:
		pick_spot()

func pick_spot() -> void:
	spot_timer = spot_recheck
	spot_lost = 0.0
	if player == null or not is_instance_valid(player):
		return
	var origin := player.global_position
	if not nav_ready or agent == null:
		var away := global_position - origin
		away.y = 0.0
		if away.length_squared() < 0.01:
			away = -global_basis.z
		spot = origin + away.normalized() * hold_distance
		return
	var claimed: Array[Vector3] = []
	for other in get_tree().get_nodes_in_group("clown"):
		if other == self:
			continue
		var other_body := other as Node3D
		if other_body != null:
			claimed.append(other_body.global_position)
	var start_angle := randf() * TAU
	var best := Vector3.ZERO
	var best_score := -INF
	for i in spot_samples:
		var angle := start_angle + TAU * float(i) / float(spot_samples)
		var radius := randf_range(hold_distance * 0.7, spot_max_distance)
		var candidate := origin + Vector3(sin(angle), 0.0, cos(angle)) * radius
		var snapped := nav_snap(candidate)
		if snapped.distance_to(candidate) > 1.3:
			continue
		if absf(snapped.y - origin.y) > 1.6:
			continue
		if not space_clear(snapped):
			continue
		var score := 8.0 if spot_sight(snapped) else 0.0
		score -= absf(snapped.distance_to(origin) - hold_distance) * 1.2
		score -= snapped.distance_to(global_position) * 0.55
		for other_position in claimed:
			if snapped.distance_to(other_position) < spot_separation:
				score -= 2.5
		if score > best_score:
			best_score = score
			best = snapped
	if best != Vector3.ZERO:
		spot = best

func spot_valid() -> bool:
	if spot == Vector3.ZERO or player == null or not is_instance_valid(player):
		return false
	var reach := Vector2(spot.x - player.global_position.x, spot.z - player.global_position.z).length()
	if reach < hold_distance * 0.5 or reach > spot_max_distance * 1.4:
		return false
	if absf(spot.y - player.global_position.y) > 1.6:
		return false
	return spot_sight(spot)

func spot_sight(point: Vector3) -> bool:
	if player == null or not is_instance_valid(player):
		return false
	var from := point + Vector3.UP * 0.45
	var to: Vector3 = player.global_position + Vector3.UP * 1.0
	var query := PhysicsRayQueryParameters3D.create(from, to, 1)
	query.exclude = [get_rid()]
	return get_world_3d().direct_space_state.intersect_ray(query).is_empty()

func space_clear(point: Vector3) -> bool:
	var from := point + Vector3.UP * 0.1
	var query := PhysicsRayQueryParameters3D.create(from, from + Vector3.UP * maxf(stand_height, 0.4), 1)
	query.exclude = [get_rid()]
	if not get_world_3d().direct_space_state.intersect_ray(query).is_empty():
		return false
	return body_clear(point)

func body_clear(point: Vector3) -> bool:
	var capsule := body_probe as CapsuleShape3D
	if capsule == null:
		capsule = CapsuleShape3D.new()
		capsule.radius = body_radius
		body_probe = capsule
	capsule.height = maxf(stand_height + body_radius * 2.0, body_radius * 2.0 + 0.1)
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = capsule
	query.collision_mask = 1
	query.collide_with_bodies = true
	query.collide_with_areas = false
	query.exclude = [get_rid()]
	query.transform = Transform3D(Basis(), point + Vector3.UP * (capsule.height * 0.5 + 0.05))
	return get_world_3d().direct_space_state.intersect_shape(query, 1).is_empty()

func nav_snap(point: Vector3) -> Vector3:
	var map := get_world_3d().navigation_map
	if not NavigationServer3D.map_is_active(map):
		return point
	return NavigationServer3D.map_get_closest_point(map, point)

func path_direction(to_spot: Vector3) -> Vector3:
	if agent != null and nav_ready:
		if agent.target_position.distance_squared_to(spot) > 0.09:
			agent.target_position = spot
		var step := agent.get_next_path_position() - global_position
		step.y = 0.0
		if step.length() > 0.15:
			return step.normalized()
	return to_spot.normalized()

func hold_spot(delta: float, to_spot: Vector3, forward: Vector3) -> Vector3:
	if to_spot.length() > 0.08:
		return to_spot.normalized() * 0.6
	sidestep_timer = maxf(sidestep_timer - delta, 0.0)
	if sidestep_timer <= 0.0:
		sidestep_sign = -sidestep_sign
		sidestep_timer = randf_range(sidestep_time_min, sidestep_time_max)
	var side := Vector3(-forward.z, 0.0, forward.x) * sidestep_sign
	if pathfinder != null and pathfinder.clearance(side, 1.1) < 0.6:
		sidestep_sign = -sidestep_sign
		return Vector3.ZERO
	if (global_position + side * spot_drift - spot).length() > spot_arrive * 2.0:
		sidestep_sign = -sidestep_sign
		return Vector3.ZERO
	return side * 0.4

func die() -> void:
	burst_left = 0
	spot = Vector3.ZERO
	spot_timer = 0.0
	spot_lost = 0.0
	super.die()

func aim(delta: float, distance: float, to_player: Vector3) -> void:
	if gun_pivot == null or muzzle == null:
		return
	var target := aim_point(distance, to_player)
	var offset := target - gun_pivot.global_position
	var flat := Vector2(offset.x, offset.z).length()
	var pitch := atan2(offset.y, maxf(flat, 0.01))
	gun_pivot.rotation.x = lerp_angle(gun_pivot.rotation.x, -pitch, clampf(delta * 9.0, 0.0, 1.0))

func aim_point(distance: float, to_player: Vector3) -> Vector3:
	if gun_pivot == null:
		return global_position
	var origin := gun_pivot.global_position
	var chest: Vector3 = player.global_position + Vector3.UP * 0.35
	sees_player = can_see(chest)
	var travel := distance / maxf(bullet_speed, 1.0)
	if sees_player:
		chest += Vector3.UP * 0.5 * bullet_gravity * travel * travel
		chest += Vector3(player.velocity.x, 0.0, player.velocity.z) * travel * lead_factor
		return chest
	var flat := Vector3(to_player.x, 0.0, to_player.z)
	if flat.length_squared() < 0.0001:
		flat = -global_basis.z
	flat = flat.normalized()
	var lift := deg_to_rad(blind_pitch + blind_lift)
	var direction := flat * cos(lift) + Vector3.UP * sin(lift)
	direction = direction.rotated(Vector3.UP, deg_to_rad(blind_yaw)).normalized()
	return origin + direction * maxf(flat.length(), 1.5)

func can_see(point: Vector3) -> bool:
	var origin := gun_pivot.global_position if gun_pivot != null else global_position + Vector3.UP * 0.3
	if origin.distance_to(point) > sight_range:
		return false
	var query := PhysicsRayQueryParameters3D.create(origin, point, 1)
	query.exclude = [get_rid()]
	return get_world_3d().direct_space_state.intersect_ray(query).is_empty()

func shoot_cycle(delta: float) -> void:
	fire_timer = maxf(fire_timer - delta, 0.0)
	if burst_left > 0:
		burst_gap_timer = maxf(burst_gap_timer - delta, 0.0)
		if burst_gap_timer <= 0.0:
			fire()
		return
	if fire_timer <= 0.0:
		burst_left = burst_size
		fire_timer = burst_cooldown
		blind_yaw = randf_range(-blind_spread, blind_spread)
		blind_pitch = randf_range(-4.0, 4.0)
		fire()

func fire() -> void:
	if muzzle == null or gun_pivot == null:
		burst_left = 0
		return
	burst_left -= 1
	burst_gap_timer = burst_gap
	var distance := 0.0
	if player != null and is_instance_valid(player):
		var flat := player.global_position - global_position
		flat.y = 0.0
		distance = flat.length()
	var target := aim_point(distance, player.global_position - global_position if player != null and is_instance_valid(player) else Vector3.ZERO)
	var direction := (target - muzzle.global_position).normalized()
	var spread := deg_to_rad(aim_spread if sees_player else blind_spread * 0.5)
	if spread > 0.0:
		direction = direction.rotated(Vector3.UP, randf_range(-spread, spread))
		var side := direction.cross(Vector3.UP)
		if side.length_squared() > 0.0001:
			direction = direction.rotated(side.normalized(), randf_range(-spread, spread))
		direction = direction.normalized()
	var bullet := BULLET_SCENE.instantiate()
	bullet.direction = direction
	bullet.damage = bullet_damage
	bullet.speed = bullet_speed
	bullet.gravity = bullet_gravity
	bullet.shooter_rid = get_rid()
	bullet.shooter = self
	bullet.pickable = false
	bullet.hit_layer = 1 | 8
	bullet.body_color = bullet_color
	get_parent().add_child(bullet)
	bullet.global_position = muzzle.global_position
	play_shot()

func update_animation() -> void:
	var horizontal := Vector2(velocity.x, velocity.z).length()
	update_bob(horizontal)
	if horizontal < 0.2:
		play_animation(hold_pose, hold_blend)
	elif horizontal > 1.1:
		play_animation("Run")
	else:
		play_animation("Walk")
