import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';

class MarkerInputDialog extends StatefulWidget {
  final double x;
  final double y;
  final String? initialText;
  final bool isEditing;
  final Function(String description) onSave;
  final VoidCallback? onDelete;

  const MarkerInputDialog({
    super.key,
    required this.x,
    required this.y,
    this.initialText,
    this.isEditing = false,
    required this.onSave,
    this.onDelete,
  });

  @override
  State<MarkerInputDialog> createState() => _MarkerInputDialogState();
}

class _MarkerInputDialogState extends State<MarkerInputDialog> {
  late TextEditingController _textController;
  bool _isValid = false;

  @override
  void initState() {
    super.initState();

    // Initialize the controller with initial text
    final initialText = widget.initialText ?? '';
    _textController = TextEditingController(text: initialText);

    _isValid = widget.isEditing || _textController.text.trim().isNotEmpty;
    _textController.addListener(_validateInput);

    // Ensure the text field shows the content and cursor is positioned correctly
    if (widget.isEditing && initialText.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          // Move cursor to end
          _textController.selection = TextSelection.fromPosition(
            TextPosition(offset: _textController.text.length),
          );
        }
      });
    }
  }

  @override
  void dispose() {
    _textController.removeListener(_validateInput);
    _textController.dispose();
    super.dispose();
  }

  void _validateInput() {
    final trimmedText = _textController.text.trim();
    // Always allow saving - empty text will delete marker when editing
    final newValid = widget.isEditing || trimmedText.isNotEmpty;

    if (newValid != _isValid) {
      setState(() {
        _isValid = newValid;
      });
    }
  }

  String _sanitizeText(String text) {
    // Remove leading/trailing whitespace and empty lines
    final lines = text.split('\n');
    final nonEmptyLines = lines.where((line) => line.trim().isNotEmpty);
    return nonEmptyLines.join('\n').trim();
  }

  void _handleSave() {
    final sanitizedText = _sanitizeText(_textController.text);
    if (sanitizedText.isEmpty) {
      // If text is empty, delete the marker (only when editing)
      if (widget.isEditing && widget.onDelete != null) {
        widget.onDelete!();
      }
    } else {
      // Save the marker with the sanitized text
      widget.onSave(sanitizedText);
    }
    Navigator.of(context).pop();
  }

  void _handleDelete() {
    if (widget.onDelete != null) {
      widget.onDelete!();
      Navigator.of(context).pop();
    }
  }

  void _handleCancel() {
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 320),
        decoration: BoxDecoration(
          color: AppTheme.backgroundColor,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.1),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Text(
                widget.isEditing ? 'Edit Note' : 'Add Note',
                style: const TextStyle(
                  fontFamily: AppTheme.primaryFont,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.bodyTextColor,
                ),
              ),

              const SizedBox(height: 16),

              // Text input
              Container(
                decoration: BoxDecoration(
                  color: AppTheme.grayColor.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AppTheme.grayColor.withValues(alpha: 0.2),
                    width: 1,
                  ),
                ),
                child: TextField(
                  controller: _textController,
                  maxLines: 4,
                  maxLength: 500,
                  autofocus: !widget
                      .isEditing, // Only autofocus when adding new marker
                  decoration: const InputDecoration(
                    hintText: 'Describe what you want to change here...',
                    hintStyle: TextStyle(
                      fontFamily: AppTheme.secondaryFont,
                      fontSize: 14,
                      color: AppTheme.grayColor,
                    ),
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.all(12),
                  ),
                  style: const TextStyle(
                    fontFamily: AppTheme.secondaryFont,
                    fontSize: 14,
                    color: AppTheme.bodyTextColor,
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Action buttons
              Row(
                children: [
                  // Delete button (only show when editing)
                  if (widget.isEditing && widget.onDelete != null) ...[
                    GestureDetector(
                      onTap: _handleDelete,
                      child: Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppTheme.errorColor.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(
                          IconsaxPlusLinear.trash,
                          size: 20,
                          color: AppTheme.errorColor,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                  ],

                  const Spacer(),

                  // Cancel button
                  GestureDetector(
                    onTap: _handleCancel,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: AppTheme.grayColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        IconsaxPlusLinear.close_circle,
                        size: 20,
                        color: AppTheme.grayColor,
                      ),
                    ),
                  ),

                  const SizedBox(width: 8),

                  // Save button
                  GestureDetector(
                    onTap: _isValid ? _handleSave : null,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: _isValid
                            ? AppTheme.primaryColor
                            : AppTheme.grayColor.withValues(alpha: 0.3),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(
                        IconsaxPlusLinear.tick_circle,
                        size: 20,
                        color: _isValid
                            ? AppTheme.backgroundColor
                            : AppTheme.grayColor,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
