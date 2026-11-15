extends Node


@export var stream: AudioStream
@export var volume_db := -6.0
@export_range(0.05, 5.0, 0.05) var overlap := 0.8

var players: Array[AudioStreamPlayer] = []
var active := 0
var length := 0.0

var cycle_time := 0.0
var fading := false
var fade_time := 0.0

const SILENT_DB := -80.0


func _ready() -> void:
	if stream == null:
		push_warning("BGMusic: no stream assigned, music will not play")
		return

	var track := stream.duplicate() as AudioStream
	unloop(track)
	length = track.get_length()
	if length <= 0.0:
		push_warning("BGMusic: stream has no length, music will not play")
		return

	overlap = clampf(overlap, 0.001, maxf(length * 0.5 - 0.001, 0.001))

	for i in 2:
		var player := AudioStreamPlayer.new()
		player.stream = track
		player.volume_db = SILENT_DB
		add_child(player)
		players.append(player)

	set_gain(players[0], 1.0)
	players[0].play()

func unloop(track: AudioStream) -> void:
	if track is AudioStreamMP3:
		(track as AudioStreamMP3).loop = false
	elif track is AudioStreamOggVorbis:
		(track as AudioStreamOggVorbis).loop = false

func _process(delta: float) -> void:
	if players.is_empty():
		return

	cycle_time += delta

	if fading:
		fade_time += delta
		var k: float = clampf(fade_time / overlap, 0.0, 1.0)
		set_gain(players[active], sin(k * PI * 0.5))
		set_gain(players[1 - active], cos(k * PI * 0.5))
		if k >= 1.0:
			fading = false
			var finished := players[1 - active]
			finished.stop()
			finished.volume_db = SILENT_DB
		return

	if cycle_time >= length - overlap:
		start_next_pass()

func start_next_pass() -> void:
	var next := 1 - active
	set_gain(players[next], 0.0)
	players[next].play()
	set_gain(players[next], 0.0)
	active = next
	cycle_time = 0.0
	fade_time = 0.0
	fading = true

func set_gain(player: AudioStreamPlayer, linear: float) -> void:
	if linear <= 0.0001:
		player.volume_db = SILENT_DB
	else:
		player.volume_db = volume_db + linear_to_db(linear)
