extends Control

const GAME_SCENE := "res://scenes/main.tscn"
const INTRO_SCENE := "res://scenes/intro.tscn"
const LOGO_START_Y := -240.0
const LOGO_FALL_TIME := 0.9
const BUTTON_START_GAP := 80.0
const BUTTON_FLY_TIME := 0.3
const BUTTON_DELAY := 0.1
const BUTTON_STAGGER := 0.07

@onready var logo: TextureRect = $Logo
@onready var play_button: TextureButton = $Play
@onready var quit_button: TextureButton = $Quit

var leaving := false
var game_scene: PackedScene


func _ready() -> void:
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	play_button.pressed.connect(play)
	quit_button.pressed.connect(quit_game)
	_request_game_scene()
	animate_in()


func _request_game_scene() -> void:
	if ResourceLoader.has_cached(GAME_SCENE):
		game_scene = ResourceLoader.load(GAME_SCENE)
		set_process(false)
		return
	ResourceLoader.load_threaded_request(GAME_SCENE)
	set_process(true)


func _process(_delta: float) -> void:
	_poll_game_scene()
	if game_scene != null:
		set_process(false)


func _poll_game_scene() -> void:
	if game_scene != null:
		return
	if ResourceLoader.load_threaded_get_status(GAME_SCENE) == ResourceLoader.THREAD_LOAD_LOADED:
		game_scene = ResourceLoader.load_threaded_get(GAME_SCENE)


func animate_in() -> void:
	var logo_target := logo.position.y
	logo.position.y = LOGO_START_Y
	var logo_tween := create_tween()
	var logo_fall := logo_tween.tween_property(logo, "position:y", logo_target, LOGO_FALL_TIME)
	logo_fall.set_trans(Tween.TRANS_BOUNCE)
	logo_fall.set_ease(Tween.EASE_OUT)

	var screen_bottom := get_viewport_rect().size.y
	var buttons: Array[TextureButton] = [play_button, quit_button]
	var last_tween: Tween = null
	for i in buttons.size():
		var button := buttons[i]
		var target := button.position.y
		button.position.y = screen_bottom + BUTTON_START_GAP
		var tween := create_tween()
		var flight := tween.tween_property(button, "position:y", target, BUTTON_FLY_TIME)
		flight.set_trans(Tween.TRANS_CUBIC)
		flight.set_ease(Tween.EASE_OUT)
		flight.set_delay(BUTTON_DELAY + i * BUTTON_STAGGER)
		last_tween = tween

	if last_tween != null:
		last_tween.finished.connect(_on_animate_in_finished)


func _on_animate_in_finished() -> void:
	play_button.grab_focus()


func play() -> void:
	if leaving:
		return
	leaving = true
	play_button.disabled = true
	quit_button.disabled = true
	get_tree().paused = false
	_poll_game_scene()
	if game_scene != null:
		get_tree().change_scene_to_packed(game_scene)
	else:
		get_tree().change_scene_to_file(GAME_SCENE)


func quit_game() -> void:
	if leaving:
		return
	leaving = true
	play_button.disabled = true
	quit_button.disabled = true
	get_tree().paused = false
	get_tree().change_scene_to_file(INTRO_SCENE)
