extends GPUParticles3D

func _ready() -> void:
	await get_tree().create_timer(lifetime + 0.25).timeout
	queue_free()
