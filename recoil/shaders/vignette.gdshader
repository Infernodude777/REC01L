shader_type canvas_item;

uniform float strength : hint_range(0.0, 1.0) = 0.0;
uniform float radius : hint_range(0.0, 1.5) = 0.30;
uniform float softness : hint_range(0.01, 1.0) = 0.45;
uniform float aspect = 1.777778;
uniform float grain_amount : hint_range(0.0, 1.0) = 0.14;
uniform float grain_size : hint_range(1.0, 8.0) = 1.5;
uniform float grain_speed : hint_range(0.0, 60.0) = 18.0;
uniform float grain_tint : hint_range(0.0, 1.0) = 0.22;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7)) + 13.7) * 43758.5453);
}

void fragment() {
	vec2 centered = UV - vec2(0.5);
	centered.x *= aspect;
	float dist = length(centered);
	float vignette = smoothstep(radius - softness, radius + softness, dist);

	vec2 cell = floor(FRAGCOORD.xy / grain_size);
	float step = floor(TIME * grain_speed);
	float noise = hash(cell + vec2(step * 17.0, step * 7.0));
	float fleck = noise * 2.0 - 1.0;

	float grain_floor = mix(0.2, 1.0, vignette);
	float alpha = clamp(vignette * strength + fleck * grain_amount * grain_floor * 0.5, 0.0, 1.0);
	float lift = max(fleck, 0.0) * grain_tint;
	COLOR = vec4(vec3(0.78, 0.76, 0.86) * lift, alpha);
}
