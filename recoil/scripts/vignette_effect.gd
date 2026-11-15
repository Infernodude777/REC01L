extends ColorRect

@export var rest_strength := 0.82
@export var peak_strength := 0.95
@export var min_hold := 3.0
@export var max_hold := 5.0
@export var fade_in_time := 1.5
@export var fade_out_time := 2.0

func _ready() -> void:
	resized.connect(update_aspect)
	update_aspect()
	apply(rest_strength)
	pulse()

func update_aspect() -> void:
	if material == null:
		return
	var view := get_viewport_rect().size
	if view.y <= 0.0:
		return
	material.set_shader_parameter("aspect", view.x / view.y)

func apply(value: float) -> void:
	if material == null:
		return
	material.set_shader_parameter("strength", value)

func pulse() -> void:
	while true:
		var hold := randf_range(min_hold, max_hold)
		var fade_in := create_tween()
		fade_in.tween_method(apply, rest_strength, peak_strength, fade_in_time)
		await fade_in.finished
		await get_tree().create_timer(hold).timeout
		var fade_out := create_tween()
		fade_out.tween_method(apply, peak_strength, rest_strength, fade_out_time)
		await fade_out.finished
