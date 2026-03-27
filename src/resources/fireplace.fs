#version 140
precision mediump float;

// Input attributes from Raylib
in vec2 fragTexCoord;
in vec4 fragColor;

// Uniforms
uniform sampler2D texture0;
uniform float uBrightness; // Range: -1.0 to 1.0 (from your code)
uniform float uTime;       // Total elapsed uTime for flicker
uniform float uIntensity;  // Fire effect strength (0.0 to 1.0)

out vec4 finalColor;

void main()
{
    // 1. Get base texture color and apply vertex tint (fragColor) 
    vec4 texelColor = texture(texture0, fragTexCoord) * fragColor;
    vec3 rgb = texelColor.rgb;

    // 2. Fireplace Flicker Logic
    // We create an organic flicker by combining two sine waves at different frequencies
    float flicker = sin(uTime * 8.0) * 0.15 + sin(uTime * 22.0) * 0.05;
    vec3 fireTint = vec3(1.0, 0.45, 0.1); // Warm orange glow
    
    // Calculate the fire's contribution based on uIntensity and flicker
    float glowPower = (0.6 + flicker) * uIntensity;
    vec3 fireGlow = fireTint * glowPower * rgb;

    // 3. Your Lightness Logic
    if (uBrightness > 0.0) {
        // Highlighting: Moves colors toward 1.0 without overshooting
        rgb = rgb + (vec3(1.0) - rgb) * uBrightness;
    }
    else {
        // Shadowing: Scales colors toward 0.0 using negative uBrightness
        rgb = rgb * (1.0 + uBrightness);
    }

    // 4. Combine base (with your uBrightness) and the additive fire glow
    vec3 finalRgb = rgb + fireGlow;

    finalColor = vec4(finalRgb, texelColor.a);
}