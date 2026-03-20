#version 330

in vec2 fragTexCoord;
in vec4 fragColor;
out vec4 finalColor;

uniform sampler2D texture0;
uniform float uIntensity; 
uniform vec2 uDirection;  
uniform float uSoftness; // New: 0.1 (sharp) to 2.0 (very soft)

void main()
{
    vec4 texelColor = texture(texture0, fragTexCoord);
    
    // Convert UV to -1.0 to 1.0
    vec2 uv = fragTexCoord * 2.0 - 1.0;
    
    // Project pixel onto the direction vector
    float projection = dot(uv, uDirection);
    
    // Control the intensity between extremities
    // We use smoothstep to create a controlled ramp
    float edge0 = -uSoftness;
    float edge1 =  uSoftness;
    float grad = smoothstep(edge0, edge1, projection);
    
    // Apply the light intensity
    // (grad - 0.5) * 2.0 maps the 0->1 gradient to -1->1 
    // so that the center of the image stays neutral if intensity is 0
    vec3 lightEffect = texelColor.rgb + (grad * uIntensity);
    
    finalColor = vec4(lightEffect, texelColor.a) * fragColor;
}