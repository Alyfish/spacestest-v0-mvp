import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/step_progress_bar.dart';

/// Choose Space - Space type selection screen
/// Users select what type of room they're redesigning
class ChooseSpaceScreen extends StatelessWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const ChooseSpaceScreen({super.key, this.onBack, this.onContinue});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: SafeArea(
        child: ChooseSpaceContent(onBack: onBack, onContinue: onContinue),
      ),
    );
  }
}

class ChooseSpaceContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const ChooseSpaceContent({super.key, this.onBack, this.onContinue});

  @override
  State<ChooseSpaceContent> createState() => _ChooseSpaceContentState();
}

class _ChooseSpaceContentState extends State<ChooseSpaceContent>
    with TickerProviderStateMixin {
  String? _selectedSpaceId;

  // Animation controllers for staggered entrance
  late List<AnimationController> _cardAnimationControllers;
  late List<Animation<double>> _cardAnimations;

  // Space types with new images
  final List<Map<String, String>> _spaceTypes = [
    {
      'id': 'living room',
      'title': 'Living Room',
      'description': 'Short description..',
      'image': 'assets/images_for_choose_spaces_new/1_pb_8pa89uOlXOTsrM8sFWg.jpg',
    },
    {
      'id': 'bedroom',
      'title': 'Bedroom',
      'description': 'Short description..',
      'image': 'assets/images_for_choose_spaces_new/unsplash_7pCFUybP_P8_house cleaning.jpg',
    },
    {
      'id': 'office',
      'title': 'Office',
      'description': 'Short description..',
      'image': 'assets/images_for_choose_spaces_new/charles-loyer-QN6fCROYdWM-unsplash.webp',
    },
    {
      'id': 'custom',
      'title': 'Custom Space',
      'description': 'Short description..',
      'image': 'assets/images_for_choose_spaces_new/Lets-Talk-About-The-Great-2018-Housing-Crash.webp',
    },
  ];

  @override
  void initState() {
    super.initState();

    // Initialize staggered animation controllers
    _cardAnimationControllers = List.generate(
      _spaceTypes.length,
      (index) => AnimationController(
        duration: const Duration(milliseconds: 400),
        vsync: this,
      ),
    );

    _cardAnimations = _cardAnimationControllers.map((controller) {
      return CurvedAnimation(
        parent: controller,
        curve: Curves.easeOutCubic,
      );
    }).toList();

    // Start staggered animations
    _startStaggeredAnimations();

    // Load existing selection
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final projectProvider = Provider.of<ProjectProvider>(
        context,
        listen: false,
      );
      final existingSpaceChosen = projectProvider.currentProject?.spaceChosen;

      if (existingSpaceChosen != null) {
        setState(() {
          _selectedSpaceId = existingSpaceChosen;
        });
      }
    });
  }

  void _startStaggeredAnimations() {
    for (int i = 0; i < _cardAnimationControllers.length; i++) {
      Future.delayed(Duration(milliseconds: i * 80), () {
        if (mounted) {
          _cardAnimationControllers[i].forward();
        }
      });
    }
  }

  @override
  void dispose() {
    for (var controller in _cardAnimationControllers) {
      controller.dispose();
    }
    super.dispose();
  }

  void _onSpaceSelected(String spaceId) {
    HapticFeedback.selectionClick();
    setState(() {
      _selectedSpaceId = spaceId;
    });
  }

  void _onContinue() {
    if (_selectedSpaceId == null) return;

    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );

    projectProvider.setSpaceChosen(_selectedSpaceId!);

    if (widget.onContinue != null) {
      widget.onContinue!();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Back button header
        _buildHeader(),

        // Progress bar
        const SizedBox(height: 8),
        const StepProgressBar(currentStep: 3, totalSteps: 8),

        // Content
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 24),

                // Title with refined typography
                Text(
                  'Choose Space.',
                  style: AppTheme.dmSans(
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                    letterSpacing: -0.5,
                  ),
                ),

                const SizedBox(height: 24),

                // 2x2 Grid of space cards
                GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    childAspectRatio: 0.78,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                  ),
                  itemCount: _spaceTypes.length,
                  itemBuilder: (context, index) {
                    final space = _spaceTypes[index];
                    final isSelected = _selectedSpaceId == space['id'];

                    return FadeTransition(
                      opacity: _cardAnimations[index],
                      child: SlideTransition(
                        position: Tween<Offset>(
                          begin: const Offset(0, 0.1),
                          end: Offset.zero,
                        ).animate(_cardAnimations[index]),
                        child: _buildSpaceCard(
                          id: space['id']!,
                          title: space['title']!,
                          description: space['description']!,
                          imagePath: space['image']!,
                          isSelected: isSelected,
                        ),
                      ),
                    );
                  },
                ),

                const SizedBox(height: 100), // Space for bottom bar
              ],
            ),
          ),
        ),

        // Bottom CTA
        _buildBottomButton(),
      ],
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 20, 0),
      child: Row(
        children: [
          // Back button
          IconButton(
            icon: const Icon(
              Icons.arrow_back_ios_new_rounded,
              size: 20,
              color: AppTheme.textPrimary,
            ),
            onPressed: widget.onBack ?? () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }

  Widget _buildSpaceCard({
    required String id,
    required String title,
    required String description,
    required String imagePath,
    required bool isSelected,
  }) {
    return GestureDetector(
      onTap: () => _onSpaceSelected(id),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOutCubic,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? AppTheme.primaryColor : Colors.transparent,
            width: isSelected ? 2 : 0,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.06),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Image fills most of the card
            Expanded(
              child: ClipRRect(
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(10),
                  topRight: Radius.circular(10),
                ),
                child: SizedBox(
                  width: double.infinity,
                  child: Image.asset(
                    imagePath,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) {
                      return Container(
                        color: AppTheme.scaffoldBackground,
                        child: Icon(
                          Icons.home_outlined,
                          size: 40,
                          color: AppTheme.textTertiary,
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),

            // Text content below image
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Title
                  Text(
                    title,
                    style: AppTheme.dmSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  // Description
                  Text(
                    description,
                    style: AppTheme.dmSans(
                      fontSize: 12,
                      fontWeight: FontWeight.w400,
                      color: AppTheme.textSecondary,
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBottomButton() {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          decoration: BoxDecoration(
            color: AppTheme.surfaceColor.withValues(alpha: 0.9),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 12,
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: SafeArea(
            top: false,
            child: SizedBox(
              width: double.infinity,
              height: 56,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _selectedSpaceId != null
                        ? AppTheme.primaryColor
                        : AppTheme.primaryColor.withValues(alpha: 0.5),
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  onPressed: _selectedSpaceId != null ? _onContinue : null,
                  child: Text(
                    'Continue',
                    style: AppTheme.dmSans(
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                      letterSpacing: 0.3,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
