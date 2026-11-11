# 编号仅在当前帧有效，不表示跨帧跟踪身份。
uint32 instance_id
uint32 class_id
string class_name
float32 confidence
# 原图像素坐标，顺序为 xmin、ymin、xmax、ymax。
float32[4] bbox_xyxy
# 原图尺寸的 mono8 掩膜：背景为 0，当前实例为 255。
sensor_msgs/Image mask
