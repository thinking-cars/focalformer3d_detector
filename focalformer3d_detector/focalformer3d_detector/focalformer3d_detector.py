import math
from typing import Any, Optional, Union

import numpy as np
import perception_msgs_utils as pmu
import rclpy
import rclpy.exceptions
from focalformer3d_detector.focalformer3d_model import Detection, FocalFormer3DModel
from numpy.lib.recfunctions import structured_to_unstructured
from perception_msgs.msg import HEXAMOTION, Object, ObjectClassification, ObjectList
from rcl_interfaces.msg import FloatingPointRange, IntegerRange, ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2

# mapping of nuScenes detection classes to perception_msgs object classification types
NUSCENES_CLASS_TO_OBJECT_CLASSIFICATION = {
    "car": ObjectClassification.CAR,
    "truck": ObjectClassification.UTILITY,
    "construction_vehicle": ObjectClassification.UTILITY,
    "bus": ObjectClassification.BUS,
    "trailer": ObjectClassification.UTILITY,
    "barrier": ObjectClassification.UNKNOWN,
    "motorcycle": ObjectClassification.MOTORCYCLE,
    "bicycle": ObjectClassification.BICYCLE,
    "pedestrian": ObjectClassification.PEDESTRIAN,
    "traffic_cone": ObjectClassification.UNKNOWN,
}


class Focalformer3DDetector(Node):
    """ROS 2 node integrating the Focalformer3D detector."""

    def __init__(self):
        """Constructor"""
        super().__init__("focalformer3d_detector")

        self.subscriber = None

        self.publisher = None

        self.auto_reconfigurable_params: list[str] = []
        self.config_file = self.declare_and_load_parameter(
            name="config_file",
            param_type=rclpy.Parameter.Type.STRING,
            description="Path to the FocalFormer3D mmdet3d config file",
            default="/docker-ros/ws/src/target/FocalFormer3D/projects/configs/focalformer3d/FocalFormer3D_L.py",
            add_to_auto_reconfigurable_params=False,
            read_only=True,
        )
        self.checkpoint_file = self.declare_and_load_parameter(
            name="checkpoint_file",
            param_type=rclpy.Parameter.Type.STRING,
            description="Path to the FocalFormer3D model checkpoint (.pth)",
            default="/docker-ros/ws/src/target/checkpoints/FocalFormer3D_L_ep6_mAP664_NDS709.pth",
            add_to_auto_reconfigurable_params=False,
            read_only=True,
        )
        self.device = self.declare_and_load_parameter(
            name="device",
            param_type=rclpy.Parameter.Type.STRING,
            description="CUDA device to run inference on",
            default="cuda:0",
            add_to_auto_reconfigurable_params=False,
            read_only=True,
        )
        self.score_threshold = self.declare_and_load_parameter(
            name="score_threshold",
            param_type=rclpy.Parameter.Type.DOUBLE,
            description="Minimum detection confidence for an object to be published",
            default=0.1,
            from_value=0.0,
            to_value=1.0,
        )
        self.intensity_scale = self.declare_and_load_parameter(
            name="intensity_scale",
            param_type=rclpy.Parameter.Type.DOUBLE,
            description="Scale factor applied to the intensity values of the input point cloud; "
            "the model was trained on nuScenes intensities in [0, 255]",
            default=1.0,
        )

        self.model = self.load_model()

        self.setup()

    def load_model(self) -> FocalFormer3DModel:
        """Loads the FocalFormer3D model from the configured config and checkpoint files

        Returns:
            FocalFormer3DModel: model ready for inference
        """

        self.get_logger().info(
            f"Loading FocalFormer3D model from config '{self.config_file}' "
            f"and checkpoint '{self.checkpoint_file}' to device '{self.device}' ..."
        )
        start_time = self.get_clock().now()
        model = FocalFormer3DModel(
            config_file=self.config_file,
            checkpoint_file=self.checkpoint_file,
            device=self.device,
        )
        loading_duration = (self.get_clock().now() - start_time).nanoseconds / 1e9
        self.get_logger().info(f"Loaded FocalFormer3D model in {loading_duration:.1f}s (classes: {model.class_names})")

        return model

    def declare_and_load_parameter(
        self,
        name: str,
        param_type: rclpy.Parameter.Type,
        description: str,
        default: Optional[Any] = None,
        add_to_auto_reconfigurable_params: bool = True,
        is_required: bool = False,
        read_only: bool = False,
        from_value: Optional[Union[int, float]] = None,
        to_value: Optional[Union[int, float]] = None,
        step_value: Optional[Union[int, float]] = None,
        additional_constraints: str = "",
    ) -> Any:
        """Declares and loads a ROS parameter

        Args:
            name (str): name
            param_type (rclpy.Parameter.Type): parameter type
            description (str): description
            default (Optional[Any], optional): default value
            add_to_auto_reconfigurable_params (bool, optional): enable reconfiguration of parameter
            is_required (bool, optional): whether failure to load parameter will stop node
            read_only (bool, optional): set parameter to read-only
            from_value (Optional[Union[int, float]], optional): parameter range minimum
            to_value (Optional[Union[int, float]], optional): parameter range maximum
            step_value (Optional[Union[int, float]], optional): parameter range step
            additional_constraints (str, optional): additional constraints description

        Returns:
            Any: parameter value
        """

        # declare parameter
        param_desc = ParameterDescriptor()
        param_desc.description = description
        param_desc.additional_constraints = additional_constraints
        param_desc.read_only = read_only
        if from_value is not None and to_value is not None:
            if param_type == rclpy.Parameter.Type.INTEGER:
                range = IntegerRange(from_value=from_value, to_value=to_value)
                if step_value is not None:
                    range.step = step_value
                param_desc.integer_range = [range]
            elif param_type == rclpy.Parameter.Type.DOUBLE:
                range = FloatingPointRange(from_value=from_value, to_value=to_value)
                if step_value is not None:
                    range.step = step_value
                param_desc.floating_point_range = [range]
            else:
                self.get_logger().warn(f"Parameter type of parameter '{name}' does not support specifying a range")
        self.declare_parameter(name, param_type, param_desc)

        # load parameter
        try:
            param = self.get_parameter(name).value
            self.get_logger().info(f"Loaded parameter '{name}': {param}")
        except rclpy.exceptions.ParameterUninitializedException:
            if is_required:
                self.get_logger().fatal(f"Missing required parameter '{name}', exiting")
                raise SystemExit(1)
            else:
                self.get_logger().warn(f"Missing parameter '{name}', using default value: {default}")
                param = default
                self.set_parameters([rclpy.Parameter(name=name, value=param)])

        # add parameter to auto-reconfigurable parameters
        if add_to_auto_reconfigurable_params:
            self.auto_reconfigurable_params.append(name)

        return param

    def parameters_callback(self, parameters: list[rclpy.Parameter]) -> SetParametersResult:
        """Handles reconfiguration when a parameter value is changed

        Args:
            parameters (list[rclpy.Parameter]): parameters

        Returns:
            SetParametersResult: parameter change result
        """

        for param in parameters:
            if param.name in self.auto_reconfigurable_params:
                setattr(self, param.name, param.value)
                self.get_logger().info(f"Reconfigured parameter '{param.name}' to: {param.value}")

        result = SetParametersResult()
        result.successful = True

        return result

    def setup(self):
        """Sets up subscribers, publishers, etc. to configure the node"""

        # callback for dynamic parameter configuration
        self.add_on_set_parameters_callback(self.parameters_callback)

        # subscriber for handling incoming messages
        self.subscriber = self.create_subscription(PointCloud2, "~/input", self.topic_callback, qos_profile=1)
        self.get_logger().info(f"Subscribed to '{self.subscriber.topic_name}'")

        # publisher for publishing outgoing messages
        self.publisher = self.create_publisher(ObjectList, "~/output", qos_profile=5)
        self.get_logger().info(f"Publishing to '{self.publisher.topic_name}'")

    def point_cloud_to_numpy(self, msg: PointCloud2) -> np.ndarray:
        """Converts a PointCloud2 message to the point array format expected by the model

        Args:
            msg (PointCloud2): point cloud message

        Returns:
            np.ndarray: point cloud of shape (N, 4) with columns (x, y, z, intensity)
        """

        field_names = [f.name for f in msg.fields]
        has_intensity = "intensity" in field_names
        read_fields = ["x", "y", "z", "intensity"] if has_intensity else ["x", "y", "z"]

        points_structured = point_cloud2.read_points(msg, field_names=read_fields, skip_nans=True)
        points = structured_to_unstructured(points_structured).astype(np.float32, copy=False)
        points = points.reshape(-1, len(read_fields))

        if has_intensity:
            points[:, 3] *= self.intensity_scale
        else:
            points = np.hstack([points, np.zeros((points.shape[0], 1), dtype=np.float32)])

        return points

    def detection_to_object(self, detection: Detection, obj_id: int, msg: PointCloud2) -> Object:
        """Converts a model detection to a perception_msgs object

        Args:
            detection (Detection): detection output by the model
            obj_id (int): object ID
            msg (PointCloud2): point cloud message the object was detected in

        Returns:
            Object: perception_msgs object
        """

        obj = Object()
        obj.id = obj_id
        obj.existence_probability = detection.score

        pmu.initialize_state(obj, HEXAMOTION.MODEL_ID)
        obj.state.header = msg.header

        # pose and dimensions in the frame of the input point cloud
        pmu.set_position_from_list(obj, list(detection.position))
        pmu.set_roll(obj, 0.0)
        pmu.set_pitch(obj, 0.0)
        pmu.set_yaw(obj, detection.yaw)
        pmu.set_length(obj, detection.dimensions[0])
        pmu.set_width(obj, detection.dimensions[1])
        pmu.set_height(obj, detection.dimensions[2])

        # velocity: model outputs (vx, vy) in sensor frame, state model expects object frame
        vx, vy = detection.velocity
        pmu.set_vel_lon(obj, math.cos(detection.yaw) * vx + math.sin(detection.yaw) * vy)
        pmu.set_vel_lat(obj, -math.sin(detection.yaw) * vx + math.cos(detection.yaw) * vy)
        pmu.set_acc_lon(obj, 0.0)
        pmu.set_acc_lat(obj, 0.0)

        classification = ObjectClassification()
        classification.type = NUSCENES_CLASS_TO_OBJECT_CLASSIFICATION.get(detection.class_name, ObjectClassification.UNCLASSIFIED)
        classification.probability = detection.score
        obj.state.classifications.append(classification)

        return obj

    def topic_callback(self, msg: PointCloud2):
        """Runs object detection on a received point cloud and publishes the detected objects

        Args:
            msg (PointCloud2): point cloud message
        """

        points = self.point_cloud_to_numpy(msg)
        if points.shape[0] == 0:
            self.get_logger().warn("Received empty point cloud, publishing empty object list", throttle_duration_sec=5)

        start_time = self.get_clock().now()
        result = self.model.detect(points, score_threshold=self.score_threshold)
        inference_duration = (self.get_clock().now() - start_time).nanoseconds / 1e9

        object_list = ObjectList()
        object_list.header = msg.header
        for obj_id, detection in enumerate(result.detections):
            object_list.objects.append(self.detection_to_object(detection, obj_id, msg))

        self.get_logger().debug(
            f"Detected {len(object_list.objects)} objects in point cloud with {points.shape[0]} points "
            f"({inference_duration * 1e3:.1f}ms)"
        )

        self.publisher.publish(object_list)


def main():
    """Initializes and spins the ROS 2 node."""

    rclpy.init()
    node = Focalformer3DDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
