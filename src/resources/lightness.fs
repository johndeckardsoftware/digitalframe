#version 140

in vec2 fragTexCoord;
in vec4 fragColor;

uniform sampler2D texture0;
uniform float brightness; // Expected range: -1.0 to 1.0

out vec4 finalColor;

void main()
{
    vec4 texelColor = texture(texture0, fragTexCoord) * fragColor;
    vec3 rgb = texelColor.rgb;

    if (brightness > 0.0) {
        // Highlighting: Moves colors toward 1.0 without overshooting
        rgb = rgb + (vec3(1.0) - rgb) * brightness;
    } 
    else {
        // Shadowing: Scales colors toward 0.0 (brightness is negative here)
        // 1.0 + (-0.5) = 0.5 multiplier
        rgb = rgb * (1.0 + brightness);
    }

    finalColor = vec4(rgb, texelColor.a);
}