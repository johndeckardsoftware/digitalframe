#version 330

in vec2 fragTexCoord;
in vec4 fragColor;
out vec4 finalColor;

uniform sampler2D texture0;
uniform vec2 uLightPos;   // Position of the light (from Python)
uniform vec3 uLightColor; // Color of the light
uniform float uRadius;    // How far the light reaches

void main()
{
    // 1. Get the current pixel color
    vec4 texelColor = texture(texture0, fragTexCoord);
    
    // 2. Calculate distance from this pixel to the light source
    // gl_FragCoord gives us the pixel position in screen space
    float distance = distance(gl_FragCoord.xy, uLightPos);
    
    // 3. Calculate "Attenuation" (how the light fades over distance)
    float attenuation = 1.0 - clamp(distance / uRadius, 0.0, 1.0);
    
    // 4. Combine: (Base Color * Ambient) + (Light Color * Intensity)
    vec3 ambient = vec3(0.1, 0.1, 0.2); // Dark blue-ish ambient light
    vec3 lightEffect = uLightColor * attenuation;
    
    finalColor = vec4(texelColor.rgb * (ambient + lightEffect), texelColor.a);
}