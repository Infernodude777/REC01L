class_name ClownPathfinder
extends RefCounted

const MODE_CLEAR := "clear"
const MODE_DUCK := "duck"
const MODE_JUMP := "jump"
const MODE_LEDGE := "ledge"
const MODE_TALL := "tall"
const MODE_FLANK := "flank"
const MODE_RETREAT := "retreat"

var body
var agent: NavigationAgent3D
var player: Node3D
var nav_ready := false

var repath_interval := 0.3
var repath_timer := 0.0
var stuck_sample := 0.0
var stuck_anchor := Vector3.ZERO
var detour := Vector3.ZERO
var detour_timer := 0.0
var hop_request := false
var long_timer := 0.0
var long_timer_left := 0.0
var long_goal := Vector3.ZERO
var long_side := 1.0
var retreat_timer := 0.0
var rng := RandomNumberGenerator.new()

func _init() -> void:
	rng.randomize()

func setup(owner_body, nav_agent: NavigationAgent3D) -> void:
	body = owner_body
	agent = nav_agent
	stuck_anchor = body.global_position
	repath_interval = float(body.repath_interval)
	long_timer = rng.randf_range(float(body.flank_interval_min), float(body.flank_interval_max)) * 0.6

func set_player(target: Node3D) -> void:
	player = target

func stand_height() -> float:
	return float(body.stand_height)

func jump_height() -> float:
	var speed := float(body.jump_speed)
	return (speed * speed) / (2.0 * float(body.gravity))

func start_retreat() -> void:
	retreat_timer = float(body.retreat_time)
	detour_timer = 0.0
	long_timer_left = 0.0

func is_retreating() -> bool:
	return retreat_timer > 0.0

func reset() -> void:
	stuck_sample = 0.0
	stuck_anchor = body.global_position
	detour = Vector3.ZERO
	detour_timer = 0.0
	hop_request = false
	retreat_timer = 0.0
	long_timer_left = 0.0
	long_timer = rng.randf_range(float(body.flank_interval_min), float(body.flank_interval_max)) * 0.6
	repath_timer = 0.0
	if agent != null:
		agent.target_position = body.global_position

func think(delta: float, to_player: Vector3, distance: float) -> Dictionary:
	var height := stand_height()
	var flat := Vector3(to_player.x, 0.0, to_player.z)
	var direct: Vector3 = -body.global_basis.z
	if flat.length_squared() > 0.0001:
		direct = flat.normalized()

	var plan := {
		"direction": direct,
		"waypoint": body.global_position,
		"jump": false,
		"duck": false,
		"slide": false,
		"climb": false,
		"retreat": false,
		"wall": false,
		"mode": MODE_CLEAR,
		"ledge_top": 0.0,
	}

	if player == null or not is_instance_valid(player):
		return plan

	if retreat_timer > 0.0:
		retreat_timer = maxf(retreat_timer - delta, 0.0)
		plan.retreat = true
		plan.mode = MODE_RETREAT
		plan.direction = -direct
		plan.waypoint = body.global_position - direct * height * 2.0
		return plan

	if agent != null and bool(body.nav_ready):
		repath_timer = maxf(repath_timer - delta, 0.0)
		if repath_timer <= 0.0:
			repath_timer = repath_interval
			if agent.target_position.distance_squared_to(player.global_position) > 0.25:
				agent.target_position = player.global_position

	var found := classify(direct, distance)
	plan.mode = found.kind
	plan.waypoint = player.global_position

	if found.kind == MODE_DUCK:
		plan.duck = true
		plan.slide = distance > height * 2.4
	elif found.kind == MODE_JUMP:
		plan.jump = true
	elif found.kind == MODE_LEDGE:
		plan.jump = true
		plan.climb = true
		plan.ledge_top = found.top
	elif found.kind == MODE_TALL:
		plan.wall = true
		var around := around_direction(direct)
		plan.direction = around
		plan.waypoint = body.global_position + around * height * 2.0
		var second := classify(around, distance)
		if second.kind == MODE_TALL:
			pick_side(direct)
			plan.direction = (around + detour * 1.2).normalized()
		elif second.kind == MODE_DUCK:
			plan.duck = true
			plan.slide = distance > height * 2.4
		elif second.kind == MODE_JUMP:
			plan.jump = true
		elif second.kind == MODE_LEDGE:
			plan.jump = true
			plan.climb = true
			plan.ledge_top = second.top
		if to_player.y > height * 1.2 and distance < height * 10.0:
			plan.climb = true

	long_timer = maxf(long_timer - delta, 0.0)
	if long_timer_left > 0.0:
		long_timer_left = maxf(long_timer_left - delta, 0.0)
		var goal_flat: Vector3 = long_goal - body.global_position
		goal_flat.y = 0.0
		if long_timer_left > 0.0 and goal_flat.length() > height * 0.7:
			var long_dir: Vector3 = goal_flat.normalized()
			var long_scan := classify(long_dir, goal_flat.length())
			if long_scan.kind != MODE_TALL:
				plan.direction = long_dir
				plan.mode = MODE_FLANK
				plan.duck = long_scan.kind == MODE_DUCK
				plan.slide = plan.duck and distance > height * 2.4
				plan.jump = long_scan.kind == MODE_JUMP or long_scan.kind == MODE_LEDGE
				plan.climb = long_scan.kind == MODE_LEDGE
				plan.ledge_top = long_scan.top
			else:
				long_timer_left = 0.0
		else:
			long_timer_left = 0.0
	elif long_timer <= 0.0 and distance > height * 3.0 and plan.mode == MODE_CLEAR:
		long_timer = rng.randf_range(float(body.flank_interval_min), float(body.flank_interval_max))
		long_side = -1.0 if rng.randf() < 0.5 else 1.0
		var perp := Vector3(-direct.z, 0.0, direct.x) * long_side
		long_goal = body.global_position + direct * height * 2.2
		long_goal += perp * rng.randf_range(height * 1.4, height * 2.8)
		long_timer_left = rng.randf_range(0.8, 1.4)

	if detour_timer > 0.0:
		detour_timer = maxf(detour_timer - delta, 0.0)
		if plan.mode != MODE_TALL:
			plan.direction = (plan.direction + detour * 1.1).normalized()

	if hop_request and not bool(body.ducked):
		plan.jump = true
		hop_request = false

	return plan

func classify(direction: Vector3, distance: float) -> Dictionary:
	var height := stand_height()
	var jump_high := jump_height()
	if direction.length_squared() < 0.0001:
		return {"kind": MODE_CLEAR, "top": 0.0}
	var probe := clampf(distance, 0.0, maxf(height * 4.0, 1.2))
	if probe < 0.08:
		return {"kind": MODE_CLEAR, "top": 0.0}
	var base: Vector3 = body.global_position
	var low_from: Vector3 = base + Vector3.UP * height * 0.18
	var high_from: Vector3 = base + Vector3.UP * height * 0.82
	var low := ray_hit(low_from, low_from + direction * probe)
	var high := ray_hit(high_from, high_from + direction * probe)
	if low.is_empty() and high.is_empty():
		return {"kind": MODE_CLEAR, "top": 0.0}
	if low.is_empty() and not high.is_empty():
		return {"kind": MODE_DUCK, "top": 0.0}
	if high.is_empty() and not low.is_empty():
		return {"kind": MODE_JUMP, "top": 0.0}
	var top := obstacle_top(low, high, height, jump_high)
	if top <= jump_high:
		return {"kind": MODE_JUMP, "top": top}
	if top <= height + jump_high:
		return {"kind": MODE_LEDGE, "top": top}
	return {"kind": MODE_TALL, "top": top}

func obstacle_top(low: Dictionary, high: Dictionary, height: float, jump_high: float) -> float:
	var anchor: Vector3
	if not low.is_empty():
		anchor = low.position
	else:
		anchor = high.position
	var start := anchor + Vector3.UP * (height + jump_high + 0.4)
	var down := ray_hit(start, start - Vector3.UP * (height + jump_high + 0.8))
	if down.is_empty():
		return 1000000.0
	return down.position.y - body.global_position.y

func around_direction(direct: Vector3) -> Vector3:
	if agent != null and bool(body.nav_ready) and not agent.is_navigation_finished():
		var nav_goal := agent.get_next_path_position()
		var nav_flat: Vector3 = nav_goal - body.global_position
		nav_flat.y = 0.0
		if nav_flat.length() > 0.15:
			return nav_flat.normalized()
	if detour_timer <= 0.0:
		pick_side(direct)
	detour_timer = maxf(detour_timer, 0.9)
	return (direct + detour * 1.25).normalized()

func pick_side(direct: Vector3) -> void:
	var height := stand_height()
	var probe := maxf(height * 5.0, 1.4)
	var left := Vector3(direct.z, 0.0, -direct.x)
	var right := -left
	var left_clear := clearance(left, probe)
	var right_clear := clearance(right, probe)
	detour = left if left_clear >= right_clear else right
	if detour.length_squared() < 0.01:
		detour = Vector3.RIGHT
	detour_timer = 1.0

func clearance(direction: Vector3, distance: float) -> float:
	var from: Vector3 = body.global_position + Vector3.UP * stand_height() * 0.5
	var hit := ray_hit(from, from + direction * distance)
	if hit.is_empty():
		return distance
	return from.distance_to(hit.position)

func duck_ahead(direction: Vector3) -> bool:
	if direction.length_squared() < 0.01:
		return false
	var height := stand_height()
	var reach := height * 0.8
	var high: Vector3 = body.global_position + Vector3.UP * height * 0.8
	var low: Vector3 = body.global_position + Vector3.UP * height * 0.12
	return not ray_hit(high, high + direction * reach).is_empty() and ray_hit(low, low + direction * reach).is_empty()

func wall_ahead(direction: Vector3) -> bool:
	if direction.length_squared() < 0.01:
		return false
	var from: Vector3 = body.global_position + Vector3.UP * stand_height() * 0.5
	return not ray_hit(from, from + direction * stand_height() * 0.9).is_empty()

func track_stuck(delta: float, direction: Vector3, distance: float) -> void:
	stuck_sample += delta
	if stuck_sample < 0.6:
		return
	var travelled: float = body.global_position.distance_to(stuck_anchor)
	stuck_anchor = body.global_position
	stuck_sample = 0.0
	if distance < stand_height() * 1.5 or travelled > 0.15:
		return
	var base := direction
	if base.length_squared() < 0.01:
		base = -body.global_basis.z
	pick_side(base)
	detour_timer = 1.2
	hop_request = true
	repath_timer = 0.0
	if agent != null and bool(body.nav_ready) and player != null:
		agent.target_position = player.global_position

func ray_hit(from: Vector3, to: Vector3) -> Dictionary:
	var query := PhysicsRayQueryParameters3D.create(from, to, 1)
	query.exclude = [body.get_rid()]
	return body.get_world_3d().direct_space_state.intersect_ray(query)
