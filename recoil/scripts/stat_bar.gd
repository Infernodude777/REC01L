extends Control

@export_group("Stat")
@export var stat_name := "health"
@export var max_stat_name := "health_max"
@export_range(0.5, 40.0, 0.5, "or_greater") var smooth := 6.0
@export var player_path: NodePath = ^"../Player"

@export_group("Nodes")
@export var fill_clip_path: NodePath = ^"FillClip"

var player: Node
var shown := 1.0
var full_width := 0.0

@onready var fill_clip: Control = get_node_or_null(fill_clip_path)

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	if not player_path.is_empty():
		player = get_node_or_null(player_path)
	if fill_clip == null:
		push_warning("%s: fill clip node not found at %s" % [name, fill_clip_path])
		return
	full_width = fill_clip.size.x
	shown = ratio()
	apply()

func _process(delta: float) -> void:
	if player == null or fill_clip == null:
		return
	shown = lerpf(shown, ratio(), clampf(delta * smooth, 0.0, 1.0))
	apply()

func ratio() -> float:
	if player == null:
		return 1.0
	var current = player.get(stat_name)
	var maximum = player.get(max_stat_name)
	if current == null or maximum == null:
		return 1.0
	return clampf(float(current) / maxf(float(maximum), 1.0), 0.0, 1.0)

func apply() -> void:
	fill_clip.size.x = full_width * shown
