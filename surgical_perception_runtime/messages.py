from surgical_perception.msg import InstrumentArray, InstrumentInstance


def to_message(prediction, header, bridge):
    message = InstrumentArray()
    message.header = header
    message.image_width = prediction.width
    message.image_height = prediction.height
    for index, instance in enumerate(prediction.instances):
        item = InstrumentInstance()
        item.instance_id = index
        item.class_id = instance.class_id
        item.class_name = instance.class_name
        item.confidence = instance.confidence
        item.bbox_xyxy = list(instance.bbox_xyxy)
        item.mask = bridge.cv2_to_imgmsg(instance.mask, encoding="mono8")
        item.mask.header = header
        message.instances.append(item)
    return message
