extends Node3D

const IMPACT_SCENE := preload("res://scenes/impact.tscn")

@export var speed := 20.0
@export var damage := 34.0
@export var gravity := 16.0
@export var restitution := 0.8
@export var impact_loss := 0.62
@export var stop_energy := 2.0
@export var hop := 3.2
@export var max_bounces := 24
@export var rest_offset := 0.11
@export_flags_3d_physics var hit_layer := 1 | 2
@export var body_color := Color(0, 0, 0, 0)
@export var shooter: Node3D
@export var pickable := true
@export var rest_lifetime := 5.0

var direction := Vector3.FORWARD
var shooter_rid: RID

var velocity := Vector3.ZERO
var bounces := 0
var prepared := false
var resting := false
var hit_lock := 0.0

func _ready() -> void:
	add_to_group("bullet")

func _physics_process(delta: float) -> void:
	if not prepared:
		prepared = true
		velocity = direction * speed
		prepare_visual()
	hit_lock = maxf(hit_lock - delta, 0.0)
	velocity.y -= gravity * delta
	var from := global_position
	var to := from + velocity * delta
	var query := PhysicsRayQueryParameters3D.create(from, to, hit_layer)
	query.collide_with_areas = true
	query.collide_with_bodies = true
	if shooter_rid.is_valid():
		query.exclude = [shooter_rid]

	var result := get_world_3d().direct_space_state.intersect_ray(query)
	if result.is_empty():
		global_position = to
		face_travel()
		return

	var point: Vector3 = result.position
	var collider: Object = result.collider
	var normal: Vector3 = result.normal
	if normal.dot(velocity) > 0.0:
		normal = -normal

	if collider is Area3D and from.distance_to(point) < 0.6:
		var area_parent := (collider as Node).get_parent()
		if area_parent == null or not area_parent.has_method("take_hit"):
			global_position = to
			return

	var target := collider as Node
	while target != null and not target.has_method("take_hit"):
		target = target.get_parent()
	if target != null and is_shooter_part(target):
		global_position = to
		face_travel()
		return
	if target != null:
		if hit_lock <= 0.0:
			target.take_hit(damage, collider.get_meta("headshot", false))
			hit_lock = 0.25
		spawn_impact(point)
		global_position = to
		face_travel()
		return

	bounce(point, normal)

func bounce(point: Vector3, normal: Vector3) -> void:
	bounces += 1
	var energy := velocity.length()
	spawn_impact(point)
	velocity = velocity.bounce(normal) * restitution * impact_loss
	if normal.y > 0.6:
		velocity.y = maxf(velocity.y, minf(hop, velocity.length() * 1.4))
	trigger_warp(point, energy)
	if energy < stop_energy or bounces > max_bounces:
		if settle(point, normal):
			return
		bounces = 0
	var heading := velocity.normalized()
	global_position = point + normal * 0.03 + heading * 0.02
	face_travel()

func settle(point: Vector3, normal: Vector3) -> bool:
	var from := point + Vector3.UP * 0.08
	var query := PhysicsRayQueryParameters3D.create(from, from + Vector3.DOWN * 0.7, 1)
	query.collide_with_areas = false
	if shooter_rid.is_valid():
		query.exclude = [shooter_rid]
	var result := get_world_3d().direct_space_state.intersect_ray(query)
	if result.is_empty():
		global_position = point + normal * 0.03
		return false
	global_position = (result.position as Vector3) + Vector3.UP * rest_offset
	var flat := Vector3(randf() - 0.5, 0.0, randf() - 0.5)
	if flat.length_squared() < 0.0001:
		flat = Vector3.RIGHT
	look_at(global_position + flat.normalized(), Vector3.UP)
	velocity = Vector3.ZERO
	resting = true
	set_physics_process(false)
	add_to_group("shell")
	if not pickable:
		get_tree().create_timer(rest_lifetime).timeout.connect(_expire)
	return true

func is_pickable() -> bool:
	return pickable

func _expire() -> void:
	if not resting:
		return
	if get_tree() == null:
		return
	queue_free()

func collect() -> void:
	queue_free()

func trigger_warp(point: Vector3, energy: float) -> void:
	var scene := get_tree().current_scene
	if scene == null or not scene.has_method("warp"):
		return
	scene.warp(point, clampf(energy / speed, 0.12, 1.0))

func face_travel() -> void:
	if velocity.length_squared() < 0.000001:
		return
	var heading := velocity.normalized()
	var up := Vector3.UP
	if absf(heading.dot(up)) > 0.99:
		up = Vector3.RIGHT
	look_at(global_position + heading, up)

func prepare_visual() -> void:
	apply_body_color()
	fit_model()
	face_travel()

func is_shooter_part(target: Node) -> bool:
	if shooter == null or not is_instance_valid(shooter):
		return false
	return target == shooter or shooter.is_ancestor_of(target)

func apply_body_color() -> void:
	if body_color.a <= 0.0:
		return
	for node in find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance.mesh == null:
			continue
		for surface in mesh_instance.mesh.get_surface_count():
			var material := mesh_instance.get_surface_override_material(surface) as StandardMaterial3D
			if material == null:
				material = mesh_instance.mesh.surface_get_material(surface) as StandardMaterial3D
			if material == null:
				continue
			var albedo := material.albedo_color
			if albedo.b <= albedo.r or albedo.b <= albedo.g:
				continue
			var tinted := material.duplicate() as StandardMaterial3D
			tinted.albedo_color = body_color
			tinted.emission_enabled = true
			tinted.emission = body_color
			tinted.emission_energy_multiplier = 0.45
			mesh_instance.set_surface_override_material(surface, tinted)

func fit_model() -> void:
	var meshes := find_children("*", "MeshInstance3D", true, false)
	if meshes.is_empty():
		return
	var origin_inverse := global_transform.affine_inverse()
	var box := AABB()
	var first := true
	for node in meshes:
		var mesh_instance := node as MeshInstance3D
		var mesh_box: AABB = (origin_inverse * mesh_instance.global_transform) * mesh_instance.get_aabb()
		box = mesh_box if first else box.merge(mesh_box)
		first = false
	var longest := maxf(box.size.x, maxf(box.size.y, box.size.z))
	if longest <= 0.0:
		return
	var fit := 0.6 / longest
	var model := get_child(0) as Node3D
	if model == null:
		return
	var fitted := global_transform * Transform3D(Basis().scaled(Vector3.ONE * fit), -box.get_center() * fit)
	model.global_transform = fitted * origin_inverse * model.global_transform

func spawn_impact(point: Vector3) -> void:
	var parent := get_tree().current_scene
	if parent == null:
		parent = get_parent()
	if parent == null:
		return
	var impact := IMPACT_SCENE.instantiate()
	parent.add_child(impact)
	impact.global_position = point
