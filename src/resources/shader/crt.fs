#version 140

in vec2 fragTexCoord;
in vec4 fragColor;
out vec4 finalColor;

uniform sampler2D texture0;
uniform float uTime;

// Helper function to curve the coordinates
vec2 curve(vec2 uv)
{
    uv = (uv - 0.5) * 2.0;
    uv *= 1;	
    uv.x *= 1.0 + pow((abs(uv.y) / 7.0), 2.0);
    uv.y *= 1.0 + pow((abs(uv.x) / 6.0), 2.0);
    uv = (uv / 2.0) + 0.5;
    uv =  uv * 0.92 + 0.04;
    return uv;
}

void main()
{
    // 1. Apply screen curvature
    vec2 uv = curve(fragTexCoord);
    
    // 2. Sample the texture (our game screen)
    vec4 texelColor = texture(texture0, uv);
    
    // 3. Create scanlines based on the Y coordinate
    float scanline = sin(uv.y * 1024.0) * 0.1;
    texelColor.rgb -= scanline;
    
    // 4. Subtle flickering effect
    texelColor.rgb *= 0.9 + 0.1 * sin(45.0 * uTime);
    
    // 5. Cut off pixels outside the curved bounds (creates black borders)
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        finalColor = vec4(0.0, 0.0, 0.0, 1.0);
    } else {
        finalColor = texelColor * fragColor;
    }
}