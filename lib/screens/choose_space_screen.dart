import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';
import 'package:spaces/providers/project_provider.dart';
import '../theme.dart';
import '../widgets/custom_outlined_button.dart';

class ChooseSpaceScreen extends StatelessWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const ChooseSpaceScreen({super.key, this.onBack, this.onContinue});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppTheme.backgroundColor,
        elevation: 0,
        toolbarHeight: 70,
        automaticallyImplyLeading: false,
        title: Row(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10.0),
              child: Image.asset(
                'assets/logo/logo.png',
                height: 100,
                width: 100,
              ),
            ),
          ],
        ),
      ),
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: ChooseSpaceContent(onBack: onBack, onContinue: onContinue),
      ),
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        backgroundColor: AppTheme.backgroundColor,
        selectedItemColor: AppTheme.primaryColor,
        unselectedItemColor: AppTheme.grayColor,
        selectedLabelStyle: const TextStyle(
          fontFamily: AppTheme.secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
        unselectedLabelStyle: const TextStyle(
          fontFamily: AppTheme.secondaryFont,
          fontSize: 12,
          fontWeight: FontWeight.w400,
        ),
        currentIndex: 0, // Home tab stays selected during flow
        onTap: (_) {}, // Disabled during flow
        items: const [
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.home),
            activeIcon: Icon(IconsaxPlusBold.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.discover),
            activeIcon: Icon(IconsaxPlusBold.discover),
            label: 'Discover',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.bag_2),
            activeIcon: Icon(IconsaxPlusBold.bag_2),
            label: 'Cart',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.bookmark),
            activeIcon: Icon(IconsaxPlusBold.bookmark),
            label: 'Saved',
          ),
          BottomNavigationBarItem(
            icon: Icon(IconsaxPlusLinear.profile_circle),
            activeIcon: Icon(IconsaxPlusBold.profile_circle),
            label: 'Profile',
          ),
        ],
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

class _ChooseSpaceContentState extends State<ChooseSpaceContent> {
  int _currentIndex = 0;
  late PageController _pageController;

  // Space types data
  final List<Map<String, String>> _spaceTypes = [
    {
      'id': 'living room',
      'title': 'living room',
      'image': 'assets/images/choose_space/choose_living.png',
    },
    {
      'id': 'bedroom',
      'title': 'bedroom',
      'image': 'assets/images/choose_space/choose_bedroom.png',
    },
    {
      'id': 'office',
      'title': 'office',
      'image': 'assets/images/choose_space/choose_office.png',
    },
    {
      'id': 'custom space',
      'title': 'custom space',
      'image': 'assets/images/choose_space/choose_custom.png',
    },
  ];

  @override
  void initState() {
    super.initState();
    _pageController = PageController(viewportFraction: 1.2);
    
    // Initialize the current index based on existing selection from ProjectProvider
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      final existingSpaceChosen = projectProvider.currentProject?.spaceChosen;
      
      if (existingSpaceChosen != null) {
        // Find the index of the existing selection
        for (int i = 0; i < _spaceTypes.length; i++) {
          if (_spaceTypes[i]['id'] == existingSpaceChosen) {
            setState(() {
              _currentIndex = i;
            });
            // Update the page controller to show the correct page
            _pageController.jumpToPage(i);
            break;
          }
        }
      }
    });
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _onPageChanged(int index) {
    setState(() {
      _currentIndex = index;
    });
  }

  void _onContinue() {
    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );
    final selectedSpace = _spaceTypes[_currentIndex]['id']!;

    // Store the selected space in the project
    projectProvider.setSpaceChosen(selectedSpace);

    if (widget.onContinue != null) {
      widget.onContinue!();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 36.0, vertical: 24.0),
      child: Column(
        children: [
          // Title section
          Row(
            children: [
              const Text('Choose Space.', style: AppTheme.sectionTitleStyle),
            ],
          ),

          const SizedBox(height: 20),

          // Carousel section
          Expanded(
            child: Column(
              children: [
                // Space carousel
                Expanded(
                  flex: 6,
                  child: PageView.builder(
                    controller: _pageController,
                    onPageChanged: _onPageChanged,
                    itemCount: _spaceTypes.length,
                    itemBuilder: (context, index) {
                      final space = _spaceTypes[index];
                      final isActive = index == _currentIndex;

                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            // Space image container
                            Expanded(

                              child: Transform.scale(
                                scaleX: index >= 1
                                    ? -1
                                    : 1, // Mirror every other item
                                child: Image.asset(
                                  space['image']!,
                                  fit: BoxFit.contain,
                                  errorBuilder: (context, error, stackTrace) {
                                    // Fallback if image doesn't exist
                                    return Container(
                                      decoration: BoxDecoration(
                                        color: AppTheme.grayColor.withValues(
                                          alpha: 0.3,
                                        ),
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

                            const SizedBox(height: 8),

                            // Space title
                            Text(
                              space['title']!,
                              style: TextStyle(
                                fontFamily: AppTheme.secondaryFont,
                                fontSize: isActive ? 40 : 32,
                                fontWeight: FontWeight.w100,
                                color: AppTheme.bodyTextColor,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),

                const SizedBox(height: 24),

                // Page indicators
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(
                    _spaceTypes.length,
                    (index) => Container(
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      width: _currentIndex == index ? 12 : 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: _currentIndex == index
                            ? AppTheme.primaryColor
                            : AppTheme.grayColor.withValues(alpha: 0.4),
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 40),

          // Action buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Back button
              CustomOutlinedButton(
                text: '',
                onPressed: widget.onBack ?? () => Navigator.pop(context),
                textColor: AppTheme.bodyTextColor,
                borderColor: Colors.transparent,
                iconColor: AppTheme.bodyTextColor,
                iconAfterText: false,
                icon: IconsaxPlusLinear.arrow_left_2,
              ),

              const SizedBox(width: 16),

              // Continue button
              CustomOutlinedButton(
                text: 'Continue',
                onPressed: _onContinue,
                textColor: AppTheme.bodyTextColor,
                borderColor: AppTheme.primaryColor,
                iconColor: AppTheme.primaryColor,
                iconAfterText: true,
                icon: IconsaxPlusLinear.arrow_right_2,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
