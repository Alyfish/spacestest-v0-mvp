import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/custom_outlined_button.dart';
// import 'ar_measurement_screen.dart';

class MeasureRoomScreen extends StatefulWidget {
  const MeasureRoomScreen({super.key, this.onBack, this.onContinue});
  final VoidCallback? onBack;
  final VoidCallback? onContinue;
  @override
  State<MeasureRoomScreen> createState() => _MeasureRoomScreenState();
}

class _MeasureRoomScreenState extends State<MeasureRoomScreen> {
  final TextEditingController _widthController = TextEditingController();
  final TextEditingController _heightController = TextEditingController();
  final TextEditingController _lengthController = TextEditingController();
  

  bool _isFormValid = false;
  final String _imagePath =
      'assets/images/measure_room.png'; // Placeholder image path

  @override
  void initState() {
    super.initState();
    
    // Initialize controllers with existing room dimensions from ProjectProvider
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = Provider.of<ProjectProvider>(context, listen: false);
      
      if (provider.roomWidth != null) {
        _widthController.text = provider.roomWidth!.toString();
      }
      if (provider.roomHeight != null) {
        _heightController.text = provider.roomHeight!.toString();
      }
      if (provider.roomLength != null) {
        _lengthController.text = provider.roomLength!.toString();
      }
      
      // Validate form after setting initial values
      _validateForm();
    });
    
    _widthController.addListener(_validateForm);
    _heightController.addListener(_validateForm);
    _lengthController.addListener(_validateForm);
  }

  @override
  void dispose() {
    _widthController.dispose();
    _heightController.dispose();
    _lengthController.dispose();
    super.dispose();
  }

  void _validateForm() {
    final width = _widthController.text.trim();
    final height = _heightController.text.trim();
    final length = _lengthController.text.trim();

    final isValid =
        width.isNotEmpty &&
        height.isNotEmpty &&
        length.isNotEmpty &&
        double.tryParse(width) != null &&
        double.tryParse(height) != null &&
        double.tryParse(length) != null;

    if (isValid != _isFormValid) {
      setState(() {
        _isFormValid = isValid;
      });
    }
  }

  // void _openCameraMode() async {
  //   // final result = await Navigator.push<Map<String, double>>(
  //   //   context,
  //   //   MaterialPageRoute(
  //   //     builder: (context) => ARMeasurementScreen(
  //   //       onMeasurementComplete: (width, height, length) {
  //   //         Navigator.of(
  //   //           context,
  //   //         ).pop({'width': width, 'height': height, 'length': length});
  //   //       },
  //   //     ),
  //   //   ),
  //   // );

  //   // if (result != null) {
  //   //   _widthController.text = result['width']?.toStringAsFixed(1) ?? '';
  //   //   _heightController.text = result['height']?.toStringAsFixed(1) ?? '';
  //   //   _lengthController.text = result['length']?.toStringAsFixed(1) ?? '';
  //   //   _validateForm();
  //   // }
  //   // AppLogger.info('Camera mode opened (AR measurement screen)');
  // }

  void _handleContinue() {
    if (!_isFormValid) return;

    final provider = Provider.of<ProjectProvider>(context, listen: false);

    // Save dimensions to provider
    provider.setRoomDimensions(
      width: double.parse(_widthController.text.trim()),
      height: double.parse(_heightController.text.trim()),
      length: double.parse(_lengthController.text.trim()),
    );

    // TODO: Navigate to next screen
    // ScaffoldMessenger.of(context).showSnackBar(
    //   const SnackBar(
    //     content: Text('Room dimensions saved!'),
    //     backgroundColor: AppTheme.primaryColor,
    //   ),
    // );
    if (widget.onContinue != null && mounted) {
      widget.onContinue!();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                const Text('Measure Room.', style: AppTheme.sectionTitleStyle),

                const SizedBox(height: 12),

                // 3D Room Image
                Center(
                  child: SizedBox(
                    width: 200,
                    height: 200,
                    child: Image.asset(
                      _imagePath,
                      fit: BoxFit.contain,
                      errorBuilder: (context, error, stackTrace) {
                        // Fallback if image doesn't exist
                        return Container(
                          decoration: BoxDecoration(
                            color: AppTheme.grayColor.withValues(alpha: 0.3),
                            borderRadius: BorderRadius.circular(24),
                          ),
                          child: const Center(
                            child: Icon(
                              IconsaxPlusLinear.home_2,
                              size: 48,
                              color: AppTheme.grayColor,
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),

                // Use Camera Button
                // Center(
                //   child: GestureDetector(
                //     onTap: _openCameraMode,
                //     child: const Text(
                //       'use camera',
                //       style: TextStyle(
                //         fontFamily: AppTheme.secondaryFont,
                //         fontSize: 30,
                //         fontWeight: FontWeight.w100,
                //         color: AppTheme.bodyTextColor,
                //       ),
                //     ),
                //   ),
                // ),

                const SizedBox(height: 12),

                // Manual Entry Section
                Text(
                  'Enter:',
                  style: AppTheme.sectionTitleStyle.copyWith(fontSize: 25),
                ),

                const SizedBox(height: 20),

                // Input Fields
                _buildInputField(
                  controller: _widthController,
                  hint: 'Width (ft)',
                ),

                const SizedBox(height: 16),

                _buildInputField(
                  controller: _heightController,
                  hint: 'Height (ft)',
                ),

                const SizedBox(height: 16),

                _buildInputField(
                  controller: _lengthController,
                  hint: 'Length (ft)',
                ),
                const SizedBox(height: 25),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    CustomOutlinedButton(
                      text: '',
                      onPressed: widget.onBack ?? () => Navigator.pop(context),
                      textColor: AppTheme.bodyTextColor,
                      borderColor: Colors.transparent,
                      iconColor: AppTheme.bodyTextColor,
                      iconAfterText: false,
                      icon: IconsaxPlusLinear.arrow_left_2,
                    ),
                    if (_isFormValid) ...[
                      const SizedBox(height: 20),
                      CustomOutlinedButton(
                        text: 'Continue',
                        icon: IconsaxPlusLinear.arrow_right_2,
                        onPressed: _handleContinue,
                        textColor: AppTheme.primaryColor,
                        borderColor: AppTheme.bodyTextColor,
                        iconColor: AppTheme.primaryColor,
                      ),
                    ],
                  ],
                ),

                // Continue Button (only visible when form is valid)
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInputField({
    required TextEditingController controller,
    required String hint,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.grayColor.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: AppTheme.grayColor.withValues(alpha: 0.2),
          width: 1,
        ),
      ),
      child: TextField(
        controller: controller,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        style: const TextStyle(
          fontFamily: AppTheme.secondaryFont,
          fontSize: 16,
          color: AppTheme.bodyTextColor,
        ),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: TextStyle(
            fontFamily: AppTheme.secondaryFont,
            fontSize: 16,
            color: AppTheme.grayColor.withValues(alpha: 0.6),
          ),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.all(16),
        ),
      ),
    );
  }
}
