#version 140

in vec2 fragTexCoord;
in vec4 fragColor;
out vec4 finalColor;

uniform sampler2D texture0;
uniform float uIntensity;
uniform vec2 uDirection;
uniform float uSoftness;

// New uniforms for color dominance
uniform vec3 uLightColor;  // Target color for highlights (e.g., Warm Yellow/White)
uniform vec3 uShadowColor; // Multiplier color for shadows (e.g., Cold Blue/Black)

void main()
{
    // Fetch the original texture color
    vec4 texelColor = texture(texture0, fragTexCoord);
    vec3 rgb = texelColor.rgb;

    // UV Remapping: Transform range from [0.0, 1.0] to [-1.0, 1.0] [cite: 3]
    // This moves the origin (0,0) to the center of the texture for correct directional math.
    vec2 uv = fragTexCoord * 2.0 - 1.0;

    // Project the current pixel onto the light direction vector [cite: 4]
    float projection = dot(uv, uDirection);

    // Create a smooth gradient based on the projection [cite: 5, 6]
    float grad = smoothstep(-uSoftness, uSoftness, projection);

    // Calculate final brightness (intensity can be positive or negative)
    float brightness = grad * uIntensity;

    // Apply color logic based on calculated brightness
    if (brightness > 0.0) {
        // Highlighting: Shift RGB channels toward the light color (uLightColor)
        // This formula ensures colors never exceed 1.0 (clipping)
        rgb = rgb + (uLightColor - rgb) * brightness;
    }
    else {
        // Shadowing: Apply the shadow tint (uShadowColor)
        // Use mix to blend original color with its "shadow-tinted" version
        // abs(brightness) converts the negative value into a 0.0 -> 1.0 factor
        rgb = mix(rgb, rgb * uShadowColor, abs(brightness));
    }

    // Final composition: Combine RGB, original Alpha, and Raylib's vertex color 
    finalColor = vec4(rgb, texelColor.a) * fragColor;
}