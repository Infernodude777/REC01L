extends Control

@onready var character_left: TextureRect = $Characters/CharacterLeft
@onready var character_right: TextureRect = $Characters/CharacterRight
@onready var character_name: Label = $DialogueUI/MarginContainer/VBoxContainer/CharacterName
@onready var dialogue_text: RichTextLabel = $DialogueUI/MarginContainer/VBoxContainer/DialogueText
@onready var continue_indicator: Label = $DialogueUI/ContinueIndicator

const GAME_SCENE := "res://scenes/main.tscn"
const POOF_SCENE := preload("res://scenes/poof.tscn")
const IMPACT_SCENE := preload("res://scenes/impact.tscn")

@export var lines: Array = []
@export var next_scene := ""
const TEXT_SPEED := 0.035
const FADE_TIME := 0.8

const SILENT_TINT := Color(0.45, 0.42, 0.5, 1.0)

const VILLAIN_LAUGH := preload("res://sounds/laugh/cartoon-villain-laugh-squeaky-cackle-bosnow-cartoon-bad-guy-laugh-villain-evil-laugh-1-0m01s.mp3")
const SILLY_LAUGH := preload("res://sounds/laugh/silly-squeaky-cartoon-giggles-ni-sound-1-00-01.mp3")

const NAMES := {
	"L": "Punch Clown",
	"R": "Shooter Clown",
	"B": "The Clowns",
}

const DIALOGUE := [
	{"speaker": "B", "text": "H-H-H-HELLOOOooooooo my little friend", "sound": SILLY_LAUGH},
	{"speaker": "L", "text": "Welcomeeee"},
	{"speaker": "B", "text": "TO OUR CIRCUS"},
	{"speaker": "L", "text": "HeHeHe", "sound": VILLAIN_LAUGH},
	{"speaker": "R", "text": "Prepare"},
	{"speaker": "R", "text": "TO MEET YOUR END", "sound": SILLY_LAUGH},
	{"speaker": "L", "text": "Use WASD to move"},
	{"speaker": "R", "text": "Left click your STUPID little mouse to shoot us"},
	{"speaker": "L", "text": "Or don't"},
	{"speaker": "L", "text": "I like to live"},
	{"speaker": "B", "text": "Hehehehe", "sound": VILLAIN_LAUGH},
	{"speaker": "R", "text": "Shift to slide", "sound": SILLY_LAUGH},
	{"speaker": "L", "text": "Hold it to stay low"},
	{"speaker": "R", "text": "and use c to side step out of the way"},
	{"speaker": "L", "text": "Slide jumping launches you SUPER FAR!!!!"},
	{"speaker": "B", "text": "Ready?", "sound": SILLY_LAUGH},
]

var line_index := -1
var typing := false
var finished := false
var char_timer := 0.0
var dialog: Array = DIALOGUE

var sfx: AudioStreamPlayer
var fade: ColorRect


func _ready() -> void:
	if not lines.is_empty():
		dialog = lines
	dialogue_text.text = ""
	character_name.text = ""
	continue_indicator.visible = false

	sfx = AudioStreamPlayer.new()
	sfx.volume_db = -4.0
	add_child(sfx)

	if get_tree().current_scene == self:
		prewarm_effects()
		prefetch_game_scene()

	for sprite: TextureRect in [character_left, character_right]:
		sprite.pivot_offset = sprite.size * 0.5
		sprite.resized.connect(_on_sprite_resized.bind(sprite))

	fade = ColorRect.new()
	fade.color = Color(0, 0, 0, 1)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(fade)

	var tween := create_tween()
	tween.tween_property(fade, "color:a", 0.0, FADE_TIME)
	await tween.finished

	show_line(0)

func _on_sprite_resized(sprite: TextureRect) -> void:
	sprite.pivot_offset = sprite.size * 0.5

func prefetch_game_scene() -> void:
	if ResourceLoader.has_cached(GAME_SCENE):
		return
	ResourceLoader.load_threaded_request(GAME_SCENE)


func prewarm_effects() -> void:
	var viewport := SubViewport.new()
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.size = Vector2i(64, 64)
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(viewport)

	var camera := Camera3D.new()
	camera.position = Vector3(0.0, 0.0, 3.0)
	camera.current = true
	viewport.add_child(camera)

	viewport.add_child(POOF_SCENE.instantiate())

	var impact := IMPACT_SCENE.instantiate()
	impact.position = Vector3(0.6, 0.0, 0.0)
	viewport.add_child(impact)

	await get_tree().create_timer(1.0).timeout
	if is_instance_valid(viewport):
		viewport.queue_free()

func _process(delta: float) -> void:
	if typing:
		char_timer += delta
		var shown := int(char_timer / TEXT_SPEED)
		if shown >= dialogue_text.get_total_character_count():
			reveal_line()
		else:
			dialogue_text.visible_characters = shown

	if continue_indicator.visible:
		continue_indicator.modulate.a = 0.55 + 0.45 * sin(Time.get_ticks_msec() * 0.006)

func _unhandled_input(event: InputEvent) -> void:
	if finished or line_index < 0:
		return
	var pressed := event.is_action_pressed("ui_accept")
	if event is InputEventMouseButton:
		var click := event as InputEventMouseButton
		pressed = click.button_index == MOUSE_BUTTON_LEFT and click.pressed
	if pressed:
		advance()
		get_viewport().set_input_as_handled()

func advance() -> void:
	if finished:
		return
	if typing:
		reveal_line()
	elif line_index + 1 >= dialog.size():
		end_intro()
	else:
		show_line(line_index + 1)

func show_line(index: int) -> void:
	line_index = index
	var line: Dictionary = dialog[index]
	var speaker: String = line["speaker"]

	character_name.text = NAMES.get(speaker, speaker)
	dialogue_text.text = line["text"]
	dialogue_text.visible_characters = 0
	char_timer = 0.0
	typing = true
	continue_indicator.visible = false

	update_sprites(speaker)

	if line.has("sound"):
		sfx.stream = line["sound"]
		sfx.play()

func reveal_line() -> void:
	typing = false
	char_timer = 0.0
	dialogue_text.visible_characters = -1
	continue_indicator.visible = true
	continue_indicator.modulate.a = 1.0

func update_sprites(speaker: String) -> void:
	pop_sprite(character_left, speaker != "R")
	pop_sprite(character_right, speaker != "L")

func pop_sprite(sprite: TextureRect, active: bool) -> void:
	var tween := create_tween().set_parallel(true)
	tween.tween_property(sprite, "modulate", Color.WHITE if active else SILENT_TINT, 0.18)
	tween.tween_property(sprite, "scale", Vector2.ONE * (1.03 if active else 0.98), 0.18)

func end_intro() -> void:
	finished = true
	typing = false
	continue_indicator.visible = false
	sfx.stop()

	var tween := create_tween()
	tween.tween_property(fade, "color:a", 1.0, FADE_TIME)
	await tween.finished
	await get_tree().create_timer(0.25).timeout
	get_tree().paused = false
	get_tree().change_scene_to_file(next_scene if next_scene != "" else GAME_SCENE)
