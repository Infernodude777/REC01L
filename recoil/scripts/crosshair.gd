extends Control

@export_group("Layout")
@export var arm_length := 7.0
@export var arm_gap := 5.0
@export var line_thickness := 2.0
@export var outline_thickness := 1.0
@export var reference_height := 1080.0

@export_group("Colours")
@export var tint := Color(1, 1, 1, 0.95)
@export var outline_tint := Color(0, 0, 0, 0.6)

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	resized.connect(queue_redraw)
	queue_redraw()

func center() -> Vector2:
	return size * 0.5

func _draw() -> void:
	var mid := center()
	var scale_factor := maxf(1.0, size.y / reference_height)
	var gap := arm_gap * scale_factor
	var arm := arm_length * scale_factor
	var thick := line_thickness * scale_factor
	var rim := outline_thickness * scale_factor
	var dirs := [Vector2.LEFT, Vector2.RIGHT, Vector2.UP, Vector2.DOWN]

	for outline_pass in [true, false]:
		var colour := outline_tint if outline_pass else tint
		var width := (thick + rim * 2.0) if outline_pass else thick
		for dir in dirs:
			draw_line(mid + dir * gap, mid + dir * (gap + arm), colour, width)
		draw_circle(mid, thick * 0.8 + (rim if outline_pass else 0.0), colour)
