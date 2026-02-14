import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/bottom_cta_bar.dart';

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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = Provider.of<ProjectProvider>(context, listen: false);
      if (provider.roomWidth != null) _widthController.text = provider.roomWidth!.toString();
      if (provider.roomHeight != null) _heightController.text = provider.roomHeight!.toString();
      if (provider.roomLength != null) _lengthController.text = provider.roomLength!.toString();
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

    final isValid = width.isNotEmpty && height.isNotEmpty && length.isNotEmpty &&
        double.tryParse(width) != null &&
        double.tryParse(height) != null &&
        double.tryParse(length) != null;

    if (isValid != _isFormValid) setState(() => _isFormValid = isValid);
  }

  void _handleContinue() {
    if (!_isFormValid) return;
    final provider = Provider.of<ProjectProvider>(context, listen: false);
    provider.setRoomDimensions(
      width: double.parse(_widthController.text.trim()),
      height: double.parse(_heightController.text.trim()),
      length: double.parse(_lengthController.text.trim()),
    );
    widget.onContinue?.call();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      appBar: AppBar(
        backgroundColor: AppTheme.scaffoldBackground,
        elevation: 0,
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, size: 20),
          color: AppTheme.bodyTextColor,
          onPressed: widget.onBack ?? () => Navigator.pop(context),
        ),
        title: Text(
          'Room Dimensions',
          style: AppTheme.headerStyle(fontSize: 18),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Instructions
                    Text(
                      'Enter your room measurements',
                      style: AppTheme.bodyStyle(
                        fontSize: 16,
                        color: AppTheme.grayColor,
                      ),
                    ),
                    const SizedBox(height: 32),

                    // Width Input
                    _buildMeasurementInput(
                      controller: _widthController,
                      label: 'Width',
                    ),
                    const SizedBox(height: 20),

                    // Length Input
                    _buildMeasurementInput(
                      controller: _lengthController,
                      label: 'Length',
                    ),
                    const SizedBox(height: 20),

                    // Height Input (Ceiling)
                    _buildMeasurementInput(
                      controller: _heightController,
                      label: 'Ceiling Height',
                    ),
                  ],
                ),
              ),
            ),
            BottomCTABar(
              primaryText: 'Continue',
              onPrimaryPressed: _isFormValid ? _handleContinue : null,
            ),
          ],
        ),
      ),
    );
  }

  /// Polished measurement input with large text and unit suffix
  Widget _buildMeasurementInput({
    required TextEditingController controller,
    required String label,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Label above input
        Text(
          label,
          style: AppTheme.labelStyle(
            fontSize: 14,
            color: AppTheme.darkGrayColor,
          ),
        ),
        const SizedBox(height: 8),
        
        // Input field
        Container(
          decoration: BoxDecoration(
            color: AppTheme.backgroundColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.grey[300]!),
          ),
          child: TextField(
            controller: controller,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: AppTheme.dmSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: AppTheme.bodyTextColor,
            ),
            decoration: InputDecoration(
              hintText: '0',
              hintStyle: AppTheme.dmSans(
                fontSize: 24,
                fontWeight: FontWeight.w400,
                color: AppTheme.grayColor,
              ),
              suffixText: 'ft',
              suffixStyle: AppTheme.dmSans(
                fontSize: 18,
                fontWeight: FontWeight.w500,
                color: AppTheme.grayColor,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 16,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
