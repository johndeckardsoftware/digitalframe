#version 140

in vec2 fragTexCoord;
in vec4 fragColor;

uniform sampler2D texture0;
uniform float uTime;
uniform float uBrightness;
uniform float uTolerance;

out vec4 finalColor;

float hash(float n) {
    return fract(sin(n) * 43758.5453);
}

float noise(float p) {
    float i = floor(p);
    float f = fract(p);
    return mix(hash(i), hash(i + 1.0), f * f * (3.0 - 2.0 * f));
}

void main()
{
    vec4 texelColor = texture(texture0, fragTexCoord) * fragColor;
    vec3 rgb = texelColor.rgb;

    vec3 blueTarget  = vec3(0.05, 0.5, 0.725);
    vec3 greenTarget = vec3(0.25, 0.6, 0.1);

    float blueDist = distance(rgb, blueTarget);
    float greenDist = distance(rgb, greenTarget);

    float isGreen = step(greenDist, blueDist);

    vec3 targetColor = mix(blueTarget, greenTarget, isGreen);
    float dist = mix(blueDist, greenDist, isGreen);

    float mask = 1.0 - smoothstep(0.0, uTolerance, dist);

    float flicker = noise(uTime * 1.0) * 0.9;
    vec3 waveColor = targetColor * (1.0 + flicker);

    vec3 brPos = rgb + (vec3(1.0) - rgb) * uBrightness;
    vec3 brNeg = rgb * (1.0 + uBrightness);
    rgb = mix(brNeg, brPos, step(0.0, uBrightness));

    vec3 finalRgb = mix(rgb, rgb * waveColor, mask);
    finalColor = vec4(finalRgb, texelColor.a);
}