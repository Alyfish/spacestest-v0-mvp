// import 'package:flutter/material.dart';

// import 'package:ar_flutter_plugin/ar_flutter_plugin.dart';
// import 'package:ar_flutter_plugin/datatypes/config_planedetection.dart';
// import 'package:ar_flutter_plugin/datatypes/node_types.dart';

// import 'package:ar_flutter_plugin/managers/ar_location_manager.dart';
// import 'package:ar_flutter_plugin/managers/ar_session_manager.dart';
// import 'package:ar_flutter_plugin/managers/ar_object_manager.dart';
// import 'package:ar_flutter_plugin/managers/ar_anchor_manager.dart';
// import 'package:ar_flutter_plugin/models/ar_anchor.dart';
// import 'package:ar_flutter_plugin/models/ar_hittest_result.dart';
// import 'package:ar_flutter_plugin/models/ar_node.dart';
// import 'package:vector_math/vector_math_64.dart' as vm;
// import 'package:iconsax_plus/iconsax_plus.dart';
// import '../theme.dart';
// import 'dart:math' as math;

// class ARMeasurementScreen extends StatefulWidget {
//   final Function(double width, double height, double length)
//   onMeasurementComplete;

//   const ARMeasurementScreen({super.key, required this.onMeasurementComplete});

//   @override
//   State<ARMeasurementScreen> createState() => _ARMeasurementScreenState();
// }

// class _ARMeasurementScreenState extends State<ARMeasurementScreen> {
//   ARSessionManager? arSessionManager;
//   ARObjectManager? arObjectManager;
//   ARAnchorManager? arAnchorManager;

//   List<ARNode> measurementNodes = [];
//   List<ARNode> lineNodes = [];
//   List<ARHitTestResult> measurementPoints = [];

//   double? roomWidth;
//   double? roomHeight;
//   double? roomLength;

//   bool isInstructionVisible = true;
//   String currentInstruction =
//       "Point your camera at the floor and tap to start measuring";
//   int measurementStep = 0;

//   @override
//   void dispose() {
//     arSessionManager?.dispose();
//     super.dispose();
//   }

//   void onARViewCreated(
//     ARSessionManager arSessionManager,
//     ARObjectManager arObjectManager,
//     ARAnchorManager arAnchorManager,
//     ARLocationManager arLocationManager,
//   ) {
//     this.arSessionManager = arSessionManager;
//     this.arObjectManager = arObjectManager;
//     this.arAnchorManager = arAnchorManager;

//     this.arSessionManager!.onInitialize(
//       showFeaturePoints: false,
//       showPlanes: true,
//       customPlaneTexturePath: "triangle.png",
//       showWorldOrigin: false,
//       handleTaps: false,
//     );
//     this.arObjectManager!.onInitialize();

//     this.arSessionManager!.onPlaneOrPointTap = onPlaneOrPointTapped;
//   }

//   Future<void> onPlaneOrPointTapped(
//     List<ARHitTestResult> hitTestResults,
//   ) async {
//     if (hitTestResults.isNotEmpty) {
//       ARHitTestResult singleHitTestResult = hitTestResults.first;

//       if (measurementStep < 4) {
//         await _addMeasurementPoint(singleHitTestResult);
//         _updateInstructions();
//       }
//     }
//   }

//   Future<void> _addMeasurementPoint(ARHitTestResult hitTestResult) async {
//     var newAnchor = ARPlaneAnchor(transformation: hitTestResult.worldTransform);
//     bool didAddAnchor = await arAnchorManager!.addAnchor(newAnchor) ?? false;

//     if (didAddAnchor) {
//       measurementPoints.add(hitTestResult);

//       // Add visual marker
//       var sphereNode = ARNode(
//         type: NodeType.webGLB,
//         uri:
//             "https://github.com/KhronosGroup/glTF-Sample-Models/raw/master/2.0/Sphere/glTF-Binary/Sphere.glb",
//         scale: vm.Vector3(0.02, 0.02, 0.02),
//         position: vm.Vector3(
//           hitTestResult.worldTransform.getColumn(3).x,
//           hitTestResult.worldTransform.getColumn(3).y,
//           hitTestResult.worldTransform.getColumn(3).z,
//         ),
//         rotation: vm.Vector4(0, 0, 0, 0),
//       );

//       bool didAddNode = await arObjectManager!.addNode(sphereNode) ?? false;
//       if (didAddNode) {
//         measurementNodes.add(sphereNode);
//       }

//       // Draw lines between points
//       if (measurementPoints.length > 1) {
//         await _drawLineBetweenPoints(
//           measurementPoints[measurementPoints.length - 2],
//           measurementPoints[measurementPoints.length - 1],
//         );
//       }

//       // Calculate measurements when we have enough points
//       if (measurementPoints.length >= 3) {
//         _calculateRoomDimensions();
//       }

//       measurementStep++;
//     }
//   }

//   Future<void> _drawLineBetweenPoints(
//     ARHitTestResult point1,
//     ARHitTestResult point2,
//   ) async {
//     // Create a line between two points
//     var distance = _calculateDistance(point1, point2);
//     var midPoint = _calculateMidpoint(point1, point2);

//     var lineNode = ARNode(
//       type: NodeType.webGLB,
//       uri:
//           "https://github.com/KhronosGroup/glTF-Sample-Models/raw/master/2.0/Box/glTF-Binary/Box.glb",
//       scale: vm.Vector3(distance, 0.01, 0.01),
//       position: vm.Vector3(midPoint.x, midPoint.y, midPoint.z),
//       rotation: vm.Vector4(0, 0, 0, 0),
//     );

//     bool didAddNode = await arObjectManager!.addNode(lineNode) ?? false;
//     if (didAddNode) {
//       lineNodes.add(lineNode);
//     }
//   }

//   double _calculateDistance(ARHitTestResult point1, ARHitTestResult point2) {
//     var pos1 = point1.worldTransform.getColumn(3);
//     var pos2 = point2.worldTransform.getColumn(3);

//     return math.sqrt(
//       math.pow(pos2.x - pos1.x, 2) +
//           math.pow(pos2.y - pos1.y, 2) +
//           math.pow(pos2.z - pos1.z, 2),
//     );
//   }

//   vm.Vector3 _calculateMidpoint(
//     ARHitTestResult point1,
//     ARHitTestResult point2,
//   ) {
//     var pos1 = point1.worldTransform.getColumn(3);
//     var pos2 = point2.worldTransform.getColumn(3);

//     return vm.Vector3(
//       (pos1.x + pos2.x) / 2,
//       (pos1.y + pos2.y) / 2,
//       (pos1.z + pos2.z) / 2,
//     );
//   }

//   void _calculateRoomDimensions() {
//     if (measurementPoints.length >= 3) {
//       // Calculate width (distance between first two points)
//       roomWidth = _calculateDistance(
//         measurementPoints[0],
//         measurementPoints[1],
//       );

//       if (measurementPoints.length >= 3) {
//         // Calculate length (distance from first point to third point)
//         roomLength = _calculateDistance(
//           measurementPoints[0],
//           measurementPoints[2],
//         );
//       }

//       if (measurementPoints.length >= 4) {
//         // Calculate height (distance from floor to ceiling point)
//         roomHeight = _calculateDistance(
//           measurementPoints[2],
//           measurementPoints[3],
//         );
//       }

//       setState(() {});
//     }
//   }

//   void _updateInstructions() {
//     setState(() {
//       switch (measurementStep) {
//         case 0:
//           currentInstruction = "Tap to place the first corner of the room";
//           break;
//         case 1:
//           currentInstruction = "Tap to place the second corner (width)";
//           break;
//         case 2:
//           currentInstruction = "Tap to place the third corner (length)";
//           break;
//         case 3:
//           currentInstruction = "Tap a point on the ceiling to measure height";
//           break;
//         case 4:
//           currentInstruction = "Measurement complete! Review your dimensions";
//           break;
//       }
//     });
//   }

//   void _resetMeasurements() async {
//     // Clear all nodes and anchors
//     for (var node in measurementNodes) {
//       await arObjectManager?.removeNode(node);
//     }
//     for (var node in lineNodes) {
//       await arObjectManager?.removeNode(node);
//     }

//     setState(() {
//       measurementNodes.clear();
//       lineNodes.clear();
//       measurementPoints.clear();
//       roomWidth = null;
//       roomHeight = null;
//       roomLength = null;
//       measurementStep = 0;
//       currentInstruction =
//           "Point your camera at the floor and tap to start measuring";
//     });
//   }

//   void _completeMeasurement() {
//     if (roomWidth != null && roomLength != null) {
//       // Convert from meters to feet (AR measurements are in meters)
//       final widthInFeet = (roomWidth! * 3.28084);
//       final lengthInFeet = (roomLength! * 3.28084);
//       final heightInFeet = roomHeight != null
//           ? (roomHeight! * 3.28084)
//           : 8.0; // Default height if not measured

//       widget.onMeasurementComplete(widthInFeet, heightInFeet, lengthInFeet);
//       Navigator.of(context).pop();
//     }
//   }

//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       backgroundColor: Colors.black,
//       body: Stack(
//         children: [
//           // AR View
//           ARView(
//             onARViewCreated: onARViewCreated,
//             planeDetectionConfig: PlaneDetectionConfig.horizontalAndVertical,
//           ),

//           // Top instruction overlay
//           Positioned(
//             top: MediaQuery.of(context).padding.top + 20,
//             left: 20,
//             right: 20,
//             child: Container(
//               padding: const EdgeInsets.all(16),
//               decoration: BoxDecoration(
//                 color: Colors.black.withValues(alpha: 0.7),
//                 borderRadius: BorderRadius.circular(12),
//               ),
//               child: Text(
//                 currentInstruction,
//                 style: const TextStyle(
//                   color: Colors.white,
//                   fontSize: 16,
//                   fontWeight: FontWeight.w500,
//                 ),
//                 textAlign: TextAlign.center,
//               ),
//             ),
//           ),

//           // Measurement display
//           if (roomWidth != null || roomLength != null || roomHeight != null)
//             Positioned(
//               top: MediaQuery.of(context).padding.top + 100,
//               left: 20,
//               child: Container(
//                 padding: const EdgeInsets.all(12),
//                 decoration: BoxDecoration(
//                   color: AppTheme.primaryColor.withValues(alpha: 0.9),
//                   borderRadius: BorderRadius.circular(8),
//                 ),
//                 child: Column(
//                   crossAxisAlignment: CrossAxisAlignment.start,
//                   children: [
//                     if (roomWidth != null)
//                       Text(
//                         'Width: ${(roomWidth! * 3.28084).toStringAsFixed(1)} ft',
//                         style: const TextStyle(
//                           color: Colors.white,
//                           fontSize: 14,
//                           fontWeight: FontWeight.w500,
//                         ),
//                       ),
//                     if (roomLength != null)
//                       Text(
//                         'Length: ${(roomLength! * 3.28084).toStringAsFixed(1)} ft',
//                         style: const TextStyle(
//                           color: Colors.white,
//                           fontSize: 14,
//                           fontWeight: FontWeight.w500,
//                         ),
//                       ),
//                     if (roomHeight != null)
//                       Text(
//                         'Height: ${(roomHeight! * 3.28084).toStringAsFixed(1)} ft',
//                         style: const TextStyle(
//                           color: Colors.white,
//                           fontSize: 14,
//                           fontWeight: FontWeight.w500,
//                         ),
//                       ),
//                   ],
//                 ),
//               ),
//             ),

//           // Bottom controls
//           Positioned(
//             bottom: MediaQuery.of(context).padding.bottom + 20,
//             left: 20,
//             right: 20,
//             child: Row(
//               children: [
//                 // Close button
//                 GestureDetector(
//                   onTap: () => Navigator.of(context).pop(),
//                   child: Container(
//                     padding: const EdgeInsets.all(12),
//                     decoration: BoxDecoration(
//                       color: Colors.white.withValues(alpha: 0.2),
//                       borderRadius: BorderRadius.circular(8),
//                     ),
//                     child: const Icon(
//                       IconsaxPlusLinear.close_circle,
//                       color: Colors.white,
//                       size: 24,
//                     ),
//                   ),
//                 ),

//                 const SizedBox(width: 12),

//                 // Reset button
//                 GestureDetector(
//                   onTap: _resetMeasurements,
//                   child: Container(
//                     padding: const EdgeInsets.all(12),
//                     decoration: BoxDecoration(
//                       color: Colors.white.withValues(alpha: 0.2),
//                       borderRadius: BorderRadius.circular(8),
//                     ),
//                     child: const Icon(
//                       IconsaxPlusLinear.refresh,
//                       color: Colors.white,
//                       size: 24,
//                     ),
//                   ),
//                 ),

//                 const Spacer(),

//                 // Complete button
//                 if (roomWidth != null && roomLength != null)
//                   GestureDetector(
//                     onTap: _completeMeasurement,
//                     child: Container(
//                       padding: const EdgeInsets.symmetric(
//                         horizontal: 20,
//                         vertical: 12,
//                       ),
//                       decoration: BoxDecoration(
//                         color: AppTheme.primaryColor,
//                         borderRadius: BorderRadius.circular(8),
//                       ),
//                       child: const Text(
//                         'Use Measurements',
//                         style: TextStyle(
//                           color: Colors.white,
//                           fontSize: 16,
//                           fontWeight: FontWeight.w600,
//                         ),
//                       ),
//                     ),
//                   ),
//               ],
//             ),
//           ),
//         ],
//       ),
//     );
//   }
// }
