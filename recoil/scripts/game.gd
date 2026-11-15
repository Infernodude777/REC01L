extends Node3D

const HITBOX_LAYER := 1
const GAME_SCENE := "res://scenes/main.tscn"
const START_SCENE := "res://scenes/start.tscn"
const END_CARD := preload("res://scenes/intro.tscn")

@export_group("Warp")
@export var warp_radius := 3.4
@export var warp_budget := 16
@export var warp_time := 1.3
@export var warp_amount := 0.045

@export_group("Laugh")
@export var laugh_cooldown_min := 10.0
@export var laugh_cooldown_max := 12.0
@export var laugh_volume_db := -5.0
@export var laugh_max_distance := 30.0
@export var laugh_unit_size := 4.0

@export_group("Navigation")
@export var agent_radius := 0.2
@export var agent_height := 0.7
@export var agent_max_climb := 0.2
@export var agent_max_slope := 45.0
@export var cell_size := 0.2
@export var cell_height := 0.1
@export var region_min_size := 2.0
@export var edge_max_error := 0.8
@export var detail_sample_distance := 4.0

@export_group("Spawns")
@export var spawn_clearance := 1.0
@export var spawn_snap_distance := 3.0
@export var spawn_body_radius := 0.16
@export var spawn_body_height := 0.62
@export var spawn_open_sides := 5
@export var spawn_room_reach := 2.5

@export_group("Playfield")
@export var playfield_inset := 0.15
@export var playfield_wall_height := 6.0
@export var playfield_wall_thickness := 0.2
@export var playfield_body_margin := 0.2
@export var playfield_bullet_leash := 1.0

@export_group("Match")
@export var max_lives := 3
@export var kills_to_win := 10

@export_group("Kills")
@export var heal_on_kill := 5.0
const LAUGH_STREAMS := [
	preload("res://sounds/laugh/cartoon-chipmunk-laugh-bosnow-short-1-00-01.mp3"),
	preload("res://sounds/laugh/cartoon-villain-laugh-squeaky-cackle-bosnow-cartoon-bad-guy-laugh-villain-evil-laugh-1-0m01s.mp3"),
	preload("res://sounds/laugh/silly-squeaky-cartoon-giggles-ni-sound-1-00-01.mp3"),
]

@onready var arena: Node3D = $Arena
@onready var spawn_points: Node3D = get_node_or_null("SpawnPoints")

var score := 0
var lives := 0
var game_over := false
var life_icons: Array[TextureRect] = []
var kill_label: Label

var laugh_ready := 0.0
var laugh_player: AudioStreamPlayer3D

var spawn_probe: Shape3D

var play_rect := Rect2()

var warp_meshes: Array[MeshInstance3D] = []
var warp_rest: Array[Transform3D] = []
var warp_centres: Array[Vector3] = []
var warps := {}

func _ready() -> void:
	lives = max_lives
	collect_life_icons()
	update_lives()
	kill_label = get_node_or_null("Kills/Row/Count")
	update_kills()
	build_playfield()
	build_arena_hitboxes()
	collect_warp_meshes()
	for clown in get_tree().get_nodes_in_group("clown"):
		clown.died.connect(on_clown_died)
	build_navigation()

func build_arena_hitboxes() -> void:
	var container := Node3D.new()
	container.name = "Hitboxes"
	arena.add_child(container)
	for node in arena.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance.mesh == null or mesh_instance.name.begins_with("NH_"):
			continue
		var concave := mesh_instance.mesh.create_trimesh_shape()
		if concave == null:
			continue
		concave.backface_collision = true
		var faces := concave.get_faces()
		var placement := mesh_instance.global_transform
		for i in faces.size():
			faces[i] = placement * faces[i]
		concave.set_faces(faces)
		var shape := CollisionShape3D.new()
		shape.shape = concave
		var body := StaticBody3D.new()
		body.name = "Hitbox_%s" % mesh_instance.name
		body.collision_layer = HITBOX_LAYER
		body.collision_mask = 0
		body.add_child(shape)
		container.add_child(body)

func build_navigation() -> void:
	var nav := NavigationMesh.new()
	nav.agent_radius = agent_radius
	nav.agent_height = agent_height
	nav.agent_max_climb = agent_max_climb
	nav.agent_max_slope = agent_max_slope
	nav.cell_size = cell_size
	nav.cell_height = cell_height
	nav.region_min_size = region_min_size
	nav.edge_max_error = edge_max_error
	nav.detail_sample_distance = detail_sample_distance
	nav.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nav.geometry_collision_mask = 1
	nav.geometry_source_geometry_mode = NavigationMesh.SOURCE_GEOMETRY_ROOT_NODE_CHILDREN

	var map := get_world_3d().navigation_map
	NavigationServer3D.map_set_cell_size(map, cell_size)
	NavigationServer3D.map_set_cell_height(map, cell_height)

	await get_tree().physics_frame
	await get_tree().physics_frame
	var data := NavigationMeshSourceGeometryData3D.new()
	NavigationServer3D.parse_source_geometry_data(nav, data, arena)
	if data.get_indices().is_empty():
		await get_tree().physics_frame
		NavigationServer3D.parse_source_geometry_data(nav, data, arena)
	NavigationServer3D.bake_from_source_geometry_data(nav, data)
	print("NAV polygons: ", nav.get_polygon_count(), " from ", data.get_indices().size(), " indices")

	var region := NavigationRegion3D.new()
	region.name = "NavRegion"
	arena.add_child(region)
	region.navigation_mesh = nav

	var tower_link := NavigationLink3D.new()
	tower_link.start_position = Vector3(6.0, 0.7, 3.0)
	tower_link.end_position = Vector3(5.3, 2.3, 1.3)
	tower_link.bidirectional = true
	arena.add_child(tower_link)

	for i in 3:
		await get_tree().physics_frame
	for clown in get_tree().get_nodes_in_group("clown"):
		clown.nav_ready = true
	place_clowns()

func collect_warp_meshes() -> void:
	for node in arena.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance.mesh == null:
			continue
		warp_meshes.append(mesh_instance)
		warp_rest.append(mesh_instance.transform)
		warp_centres.append((mesh_instance.global_transform * mesh_instance.get_aabb()).get_center())

func warp(point: Vector3, strength: float) -> void:
	var nearby := []
	for i in warp_meshes.size():
		var distance := warp_centres[i].distance_to(point)
		if distance < warp_radius:
			nearby.append([distance, i])
	if nearby.is_empty():
		return
	nearby.sort()
	var count := mini(nearby.size(), warp_budget)
	for k in count:
		var index := int(nearby[k][1])
		var distance := float(nearby[k][0])
		var falloff := 1.0 - distance / warp_radius
		var push := warp_centres[index] - point
		push.y = 0.0
		if push.length_squared() < 0.0001:
			push = Vector3(randf_range(-1.0, 1.0), 0.0, randf_range(-1.0, 1.0))
		warps[index] = {
			"time": 0.0,
			"dir": push.normalized(),
			"amount": warp_amount * strength * falloff * falloff,
			"freq": randf_range(15.0, 23.0),
			"decay": randf_range(4.5, 6.5),
		}

func build_playfield() -> void:
	var lo := Vector3(INF, INF, INF)
	var hi := Vector3(-INF, -INF, -INF)
	var found := false
	for node in arena.find_children("Trim*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		var box: AABB = mesh_instance.global_transform * mesh_instance.get_aabb()
		lo = lo.min(box.position)
		hi = hi.max(box.end)
		found = true
	if not found:
		return
	var rect := Rect2(Vector2(lo.x, lo.z), Vector2(hi.x - lo.x, hi.z - lo.z)).grow(-playfield_inset)
	if rect.size.x <= 0.0 or rect.size.y <= 0.0:
		return
	play_rect = rect
	build_playfield_walls(rect, lo.y)

func build_playfield_walls(rect: Rect2, base_y: float) -> void:
	var container := Node3D.new()
	container.name = "PlayfieldWalls"
	arena.add_child(container)
	var height := playfield_wall_height
	var thickness := playfield_wall_thickness
	var centre := rect.get_center()
	var y := base_y + height * 0.5
	add_playfield_wall(container, Vector3(centre.x, y, rect.position.y), Vector3(rect.size.x + thickness * 2.0, height, thickness))
	add_playfield_wall(container, Vector3(centre.x, y, rect.end.y), Vector3(rect.size.x + thickness * 2.0, height, thickness))
	add_playfield_wall(container, Vector3(rect.position.x, y, centre.y), Vector3(thickness, height, rect.size.y + thickness * 2.0))
	add_playfield_wall(container, Vector3(rect.end.x, y, centre.y), Vector3(thickness, height, rect.size.y + thickness * 2.0))

func add_playfield_wall(parent: Node3D, point: Vector3, size: Vector3) -> void:
	var box := BoxShape3D.new()
	box.size = size
	var shape := CollisionShape3D.new()
	shape.shape = box
	var body := StaticBody3D.new()
	body.collision_layer = HITBOX_LAYER
	body.collision_mask = 0
	body.add_child(shape)
	parent.add_child(body)
	body.global_position = point

func inside_playfield(point: Vector3, margin := 0.0) -> bool:
	if not play_rect.has_area():
		return true
	var centre := play_rect.get_center()
	if absf(point.x - centre.x) > play_rect.size.x * 0.5 - margin:
		return false
	return absf(point.z - centre.y) <= play_rect.size.y * 0.5 - margin

func keep_inside(body: Node3D) -> void:
	if body == null or not play_rect.has_area():
		return
	var centre := play_rect.get_center()
	var limit_x := maxf(play_rect.size.x * 0.5 - playfield_body_margin, 0.05)
	var limit_z := maxf(play_rect.size.y * 0.5 - playfield_body_margin, 0.05)
	var point := body.global_position
	var moved := false
	var dx := point.x - centre.x
	if absf(dx) > limit_x:
		point.x = centre.x + signf(dx) * limit_x
		moved = true
	var dz := point.z - centre.y
	if absf(dz) > limit_z:
		point.z = centre.y + signf(dz) * limit_z
		moved = true
	if moved:
		body.global_position = point

func _physics_process(_delta: float) -> void:
	if not play_rect.has_area():
		return
	for node in get_tree().get_nodes_in_group("clown"):
		keep_inside(node as Node3D)
	keep_inside(get_tree().get_first_node_in_group("player") as Node3D)
	for node in get_tree().get_nodes_in_group("bullet"):
		var bullet := node as Node3D
		if bullet != null and not inside_playfield(bullet.global_position, -playfield_bullet_leash):
			bullet.queue_free()

func _process(delta: float) -> void:
	if warps.is_empty():
		return
	var done := []
	for index in warps:
		var state: Dictionary = warps[index]
		state.time += delta
		var wave: float = sin(state.time * state.freq) * exp(-state.time * state.decay)
		var mesh := warp_meshes[index]
		var rest := warp_rest[index]
		var amount: float = state.amount
		var squeeze: float = 1.0 + amount * 2.0 * wave
		var offset: Vector3 = state.dir * amount * wave
		var basis := rest.basis * Basis.from_scale(Vector3(squeeze, 1.0 / clampf(squeeze, 0.3, 3.0), squeeze))
		mesh.transform = Transform3D(basis, rest.origin + offset)
		if state.time > warp_time:
			mesh.transform = rest
			done.append(index)
	for index in done:
		warps.erase(index)

func pick_spawn(clown: Node3D) -> Transform3D:
	if spawn_points == null or spawn_points.get_child_count() == 0:
		return clown.global_transform
	var spots := collect_spawn_positions(true)
	if spots.is_empty():
		spots = widest_spawn_positions(collect_spawn_positions(false))
	if spots.is_empty():
		return clown.global_transform

	var links: Array[int] = []
	links.resize(spots.size())
	links.fill(0)
	for i in spots.size():
		for j in range(i + 1, spots.size()):
			if spawn_linked(spots[i], spots[j]):
				links[i] += 1
				links[j] += 1
	var best_links := 0
	for count in links:
		best_links = maxi(best_links, count)

	var taken := []
	for other in get_tree().get_nodes_in_group("clown"):
		if other != clown:
			taken.append((other as Node3D).global_position)

	var open_choices: Array[Vector3] = []
	var linked_choices: Array[Vector3] = []
	for i in spots.size():
		if links[i] != best_links:
			continue
		linked_choices.append(spots[i])
		var free := true
		for position in taken:
			if spots[i].distance_to(position) < spawn_clearance:
				free = false
				break
		if free:
			open_choices.append(spots[i])
	var pool := open_choices if not open_choices.is_empty() else linked_choices
	if pool.is_empty():
		return clown.global_transform
	var chosen: Vector3 = pool.pick_random()
	return Transform3D(clown.global_basis.rotated(Vector3.UP, randf() * TAU), chosen)

func place_clowns() -> void:
	var taken: Array[Vector3] = []
	for clown in get_tree().get_nodes_in_group("clown"):
		var body := clown as Node3D
		if body == null:
			continue
		var start := body.global_position
		var point := start
		if not spawn_open(start):
			point = find_open_near(start, taken)
			if not point.is_finite():
				point = pick_spawn(body).origin
		if point.is_finite() and point.distance_to(start) > 0.01:
			body.global_position = point
			if body.has_method("reset_stance"):
				body.reset_stance()
			taken.append(point)
		else:
			taken.append(start)

func find_open_near(from: Vector3, taken: Array[Vector3]) -> Vector3:
	var map := get_world_3d().navigation_map
	var radii: Array[float] = [0.7, 1.4, 2.2, 3.2, 4.4, 5.8]
	var best := Vector3(INF, INF, INF)
	var best_distance := INF
	for ring in radii:
		for i in 12:
			var angle := TAU * float(i) / 12.0 + ring
			var candidate := from + Vector3(sin(angle), 0.0, cos(angle)) * ring
			if NavigationServer3D.map_is_active(map):
				candidate = NavigationServer3D.map_get_closest_point(map, candidate)
			if candidate.distance_to(from) > ring + 1.5:
				continue
			if not spawn_open(candidate):
				continue
			var shared := false
			for position in taken:
				if candidate.distance_to(position) < spawn_clearance:
					shared = true
					break
			if shared:
				continue
			var distance := candidate.distance_to(from)
			if distance < best_distance:
				best_distance = distance
				best = candidate
		if best.is_finite():
			return best
	return best

func collect_spawn_positions(require_open: bool) -> Array[Vector3]:
	var spots: Array[Vector3] = []
	for marker in spawn_points.get_children():
		var spot := marker as Node3D
		if spot == null:
			continue
		var position := spawn_position(spot.global_position, require_open)
		if position.is_finite():
			spots.append(position)
	return spots

func spawn_position(marker_position: Vector3, require_open: bool) -> Vector3:
	var point := marker_position
	var map := get_world_3d().navigation_map
	if NavigationServer3D.map_is_active(map):
		var snapped := NavigationServer3D.map_get_closest_point(map, marker_position)
		if snapped.distance_to(marker_position) <= spawn_snap_distance:
			point = snapped
	if not inside_playfield(point, spawn_body_radius):
		return Vector3(INF, INF, INF)
	if require_open and not (spawn_open(point) and spawn_room(point)):
		return Vector3(INF, INF, INF)
	return point

func spawn_open(point: Vector3) -> bool:
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = spawn_body_shape()
	query.collision_mask = HITBOX_LAYER
	query.collide_with_bodies = true
	query.collide_with_areas = false
	query.transform = Transform3D(Basis(), point + Vector3.UP * (spawn_body_height * 0.5 + 0.06))
	return get_world_3d().direct_space_state.intersect_shape(query, 1).is_empty()

func spawn_body_shape() -> Shape3D:
	if spawn_probe == null:
		var capsule := CapsuleShape3D.new()
		capsule.radius = spawn_body_radius
		capsule.height = maxf(spawn_body_height, spawn_body_radius * 2.0)
		spawn_probe = capsule
	return spawn_probe

func spawn_room(point: Vector3) -> bool:
	return room_score(point) >= spawn_open_sides

func room_score(point: Vector3) -> int:
	var space := get_world_3d().direct_space_state
	var from := point + Vector3.UP * (spawn_body_height * 0.6)
	var clear := 0
	for i in 8:
		var angle := TAU * float(i) / 8.0
		var to := from + Vector3(sin(angle), 0.0, cos(angle)) * spawn_room_reach
		var query := PhysicsRayQueryParameters3D.create(from, to, HITBOX_LAYER)
		query.collide_with_areas = false
		if space.intersect_ray(query).is_empty():
			clear += 1
	return clear

func widest_spawn_positions(pool: Array[Vector3]) -> Array[Vector3]:
	var best := -1
	var scores: Array[int] = []
	for point in pool:
		var score := room_score(point)
		scores.append(score)
		best = maxi(best, score)
	var keep: Array[Vector3] = []
	for i in pool.size():
		if scores[i] == best:
			keep.append(pool[i])
	return keep

func spawn_linked(from: Vector3, to: Vector3) -> bool:
	var map := get_world_3d().navigation_map
	if not NavigationServer3D.map_is_active(map):
		return true
	var target := NavigationServer3D.map_get_closest_point(map, to)
	if target.distance_to(to) > spawn_snap_distance:
		return false
	var path := NavigationServer3D.map_get_path(map, from, target, true)
	if path.size() < 2:
		return false
	return path[path.size() - 1].distance_to(target) <= 0.8

func on_clown_died() -> void:
	score += 1
	update_kills()
	var player := get_tree().get_first_node_in_group("player")
	if player != null and player.has_method("heal"):
		player.heal(heal_on_kill)
	if score >= kills_to_win:
		end_game(true)

func collect_life_icons() -> void:
	life_icons.clear()
	var row := get_node_or_null("Lives/Row")
	if row == null:
		return
	for node in row.get_children():
		var icon := node as TextureRect
		if icon != null:
			life_icons.append(icon)

func update_lives() -> void:
	for i in life_icons.size():
		life_icons[i].visible = i < lives

func update_kills() -> void:
	if kill_label != null:
		kill_label.text = "x %d / %d" % [score, kills_to_win]

func on_player_died() -> bool:
	if game_over:
		return false
	lives = maxi(lives - 1, 0)
	update_lives()
	if lives <= 0:
		end_game(false)
		return false
	return true

func end_game(won: bool) -> void:
	if game_over:
		return
	game_over = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var card = END_CARD.instantiate()
	card.lines = [{"speaker": "B", "text": "YOU WIN" if won else "YOU LOSE"}]
	card.next_scene = START_SCENE
	card.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(card)
	get_tree().paused = true

func clear_shooter_bullets(shooter: Node, include_resting := false) -> void:
	if shooter == null:
		return
	for node in get_tree().get_nodes_in_group("bullet"):
		if node.get("shooter") != shooter:
			continue
		if not include_resting and node.get("resting") == true:
			continue
		node.queue_free()

func clown_laugh(position: Vector3, clown: Node) -> void:
	var now := Time.get_ticks_msec() / 1000.0
	if now < laugh_ready:
		return
	laugh_ready = now + randf_range(laugh_cooldown_min, laugh_cooldown_max)
	if laugh_player == null:
		laugh_player = AudioStreamPlayer3D.new()
		laugh_player.max_distance = laugh_max_distance
		laugh_player.unit_size = laugh_unit_size
		laugh_player.volume_db = laugh_volume_db
		add_child(laugh_player)
	laugh_player.stream = LAUGH_STREAMS.pick_random()
	laugh_player.global_position = position + Vector3.UP * 0.5
	laugh_player.play()
	if clown != null and is_instance_valid(clown) and clown.has_method("laugh"):
		clown.laugh()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("restart"):
		get_tree().reload_current_scene()
