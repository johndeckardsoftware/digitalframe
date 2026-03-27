from pyray import set_target_fps

fps = 0             # frame per second
ft = 0              # frame time in second (fps/60)
rft = 0             # real frame time 
stack_fps = []

def push_set_fps(new_fps):
    global fps, ft, rft
    stack_fps.append(fps)
    prev_fps = fps
    fps = new_fps
    ft = 1 / fps
    rft = ft
    set_target_fps(new_fps)
    return prev_fps

def pop_set_fps():
    if len(stack_fps) == 0: return None

    global fps, ft, rft
    prev_fps = fps
    fps = stack_fps.pop()
    ft = 1 / fps
    rft = ft
    set_target_fps(fps)   
    return prev_fps

def get_fps():
    global fps
    return fps

def set_fps(new_fps):
    global fps, ft, rft, stack_fps
    #stack_fps.clear()
    fps = new_fps
    ft = 1 / fps
    rft = ft
    set_target_fps(new_fps)
