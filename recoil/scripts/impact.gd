extends MeshInstance3D

@export var shrink_time := 0.18

func _ready() -> void:
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3.ZERO, shrink_time)
	tween.tween_callback(queue_free)
