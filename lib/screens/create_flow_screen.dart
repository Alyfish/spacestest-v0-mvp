import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/project_provider.dart';
import '../theme.dart';
import '../widgets/app_bottom_nav_bar.dart';

// Import all flow screens
import 'upload_photo_screen.dart';
import 'confirm_selection_screen.dart';
import 'choose_space_screen.dart';
import 'describe_custom_space_screen.dart';
import 'choose_items_screen.dart';
import 'upload_inspiration_screen.dart';
import 'confirm_inspiration_screen.dart';
import 'choose_approach_screen.dart';
import 'preferred_stores_screen.dart';
import 'analyzing_screen.dart';
import 'improvements_screen.dart';
import 'main_navigation_screen.dart';
import 'dream_space_screen.dart';
import 'choose_products_screen.dart';
import 'describe_changes_screen.dart';
import '../models/shop_product.dart';

/// Enum representing each step in the create/redesign flow
enum CreateFlowStep {
  uploadPhoto,        // Step 1
  confirmSelection,   // Step 2
  chooseSpace,        // Step 3
  describeCustomSpace,// Step 3 (conditional)
  chooseItems,        // Step 4
  chooseApproach,     // Step 5
  preferredStores,    // Step 6
  analyzing,          // Step 7
  improvements,       // Step 8
  improvementsAnalyzing, // Step 9 (after clicking Improve)
  dreamSpace,         // Step 10 (generated room with hotspots)
  chooseProducts,     // Step 11 (product grid for selected hotspot)
  describeChanges,    // Step 12 (retry - describe changes)
  // Optional inspiration steps (not in main flow)
  uploadInspiration,
  confirmInspiration,
}

/// Full-screen route that manages the redesign flow.
/// Pushed from Home - completely separate from bottom navigation.
class CreateFlowScreen extends StatefulWidget {
  const CreateFlowScreen({super.key});

  @override
  State<CreateFlowScreen> createState() => _CreateFlowScreenState();
}

class _CreateFlowScreenState extends State<CreateFlowScreen> {
  CreateFlowStep _currentStep = CreateFlowStep.uploadPhoto;
  ProductHotspot? _selectedHotspot;

  void _goToStep(CreateFlowStep step) {
    setState(() => _currentStep = step);
  }

  void _goToProducts(ProductHotspot hotspot) {
    setState(() {
      _selectedHotspot = hotspot;
      _currentStep = CreateFlowStep.chooseProducts;
    });
  }

  void _goBack() {
    switch (_currentStep) {
      case CreateFlowStep.uploadPhoto:
        Navigator.of(context).pop(); // Exit flow
        break;
      case CreateFlowStep.confirmSelection:
        _goToStep(CreateFlowStep.uploadPhoto);
        break;
      case CreateFlowStep.chooseSpace:
        _goToStep(CreateFlowStep.confirmSelection);
        break;
      case CreateFlowStep.describeCustomSpace:
        _goToStep(CreateFlowStep.chooseSpace);
        break;
      case CreateFlowStep.chooseItems:
        // Check if user came from custom space
        final provider = Provider.of<ProjectProvider>(context, listen: false);
        if (provider.currentProject?.spaceChosen == 'custom') {
          _goToStep(CreateFlowStep.describeCustomSpace);
        } else {
          _goToStep(CreateFlowStep.chooseSpace);
        }
        break;
      case CreateFlowStep.chooseApproach:
        _goToStep(CreateFlowStep.chooseItems);
        break;
      case CreateFlowStep.uploadInspiration:
        _goToStep(CreateFlowStep.chooseItems);
        break;
      case CreateFlowStep.confirmInspiration:
        _goToStep(CreateFlowStep.uploadInspiration);
        break;
      case CreateFlowStep.preferredStores:
        _goToStep(CreateFlowStep.chooseApproach);
        break;
      case CreateFlowStep.analyzing:
        _goToStep(CreateFlowStep.preferredStores);
        break;
      case CreateFlowStep.improvements:
        _goToStep(CreateFlowStep.preferredStores);
        break;
      case CreateFlowStep.improvementsAnalyzing:
        _goToStep(CreateFlowStep.improvements);
        break;
      case CreateFlowStep.dreamSpace:
        // Can't go back from dream space - it's the result
        // User should use Restart button instead
        break;
      case CreateFlowStep.chooseProducts:
        _goToStep(CreateFlowStep.dreamSpace);
        break;
      case CreateFlowStep.describeChanges:
        _goToStep(CreateFlowStep.dreamSpace);
        break;
    }
  }

  void _handleNavTap(int index) {
    if (index == 2) return; // FAB position
    if (index == 1) {
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.lock_outline, color: Colors.white, size: 18),
              const SizedBox(width: 12),
              Text('Coming soon', style: AppTheme.dmSans(fontSize: 14, fontWeight: FontWeight.w500, color: Colors.white)),
            ],
          ),
          backgroundColor: AppTheme.textSecondary,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          margin: const EdgeInsets.all(16),
          duration: const Duration(seconds: 2),
        ),
      );
      return;
    }
    // Navigate to main navigation (home/saved/profile)
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const MainNavigationScreen()),
      (route) => false,
    );
  }

  Future<void> _handleFabPressed() async {
    try {
      final projectProvider = Provider.of<ProjectProvider>(context, listen: false);
      await projectProvider.createProject(context);
      if (mounted) {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const MainNavigationScreen()),
          (route) => false,
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to start: ${e.toString()}'), backgroundColor: AppTheme.errorColor),
        );
      }
    }
  }

  /// Check if the current step already has its own Scaffold with nav bar
  bool _stepHasOwnScaffold(CreateFlowStep step) {
    return step == CreateFlowStep.improvements ||
           step == CreateFlowStep.improvementsAnalyzing ||
           step == CreateFlowStep.analyzing ||
           step == CreateFlowStep.dreamSpace ||
           step == CreateFlowStep.chooseProducts ||
           step == CreateFlowStep.describeChanges;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _currentStep == CreateFlowStep.uploadPhoto,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          _goBack();
        }
      },
      child: _stepHasOwnScaffold(_currentStep)
          ? _buildCurrentStep()
          : Scaffold(
              backgroundColor: AppTheme.scaffoldBackground,
              body: SafeArea(
                bottom: false,
                child: _buildCurrentStep(),
              ),
              bottomNavigationBar: AppBottomNavBar(
                selectedIndex: 0,
                onItemTapped: _handleNavTap,
                onFabPressed: _handleFabPressed,
              ),
            ),
    );
  }

  Widget _buildCurrentStep() {
    switch (_currentStep) {
      case CreateFlowStep.uploadPhoto:
        return UploadPhotoContent(
          onBack: _goBack,
          onConfirmSelection: () => _goToStep(CreateFlowStep.confirmSelection),
        );
      
      case CreateFlowStep.confirmSelection:
        return ConfirmSelectionContent(
          onBack: _goBack,
          onSuccess: () => _goToStep(CreateFlowStep.chooseSpace),
        );
      
      case CreateFlowStep.chooseSpace:
        return ChooseSpaceContent(
          onBack: _goBack,
          onContinue: () {
            // Check if custom space was selected
            final provider = Provider.of<ProjectProvider>(context, listen: false);
            if (provider.currentProject?.spaceChosen == 'custom') {
              _goToStep(CreateFlowStep.describeCustomSpace);
            } else {
              _goToStep(CreateFlowStep.chooseItems);
            }
          },
        );

      case CreateFlowStep.describeCustomSpace:
        return DescribeCustomSpaceScreen(
          onBack: _goBack,
          onContinue: () => _goToStep(CreateFlowStep.chooseItems),
        );

      case CreateFlowStep.chooseItems:
        return ChooseItemsContent(
          onBack: _goBack,
          onContinue: () => _goToStep(CreateFlowStep.chooseApproach),
        );

      case CreateFlowStep.uploadInspiration:
        return UploadInspirationContent(
          onBack: _goBack,
          onConfirmSelection: () => _goToStep(CreateFlowStep.confirmInspiration),
          onSkipToApproach: () => _goToStep(CreateFlowStep.chooseApproach),
        );
      
      case CreateFlowStep.confirmInspiration:
        return ConfirmInspirationContent(
          onBack: _goBack,
          onSuccess: () => _goToStep(CreateFlowStep.chooseApproach),
        );
      
      case CreateFlowStep.chooseApproach:
        return ChooseApproachContent(
          onBack: _goBack,
          onContinue: () => _goToStep(CreateFlowStep.preferredStores),
        );
      
      case CreateFlowStep.preferredStores:
        return PreferredStoresContent(
          onBack: _goBack,
          onContinue: () => _goToStep(CreateFlowStep.analyzing),
        );
      
      case CreateFlowStep.analyzing:
        return AnalyzingScreen(
          onBack: _goBack,
          onComplete: () => _goToStep(CreateFlowStep.improvements),
        );
      
      case CreateFlowStep.improvements:
        return ImprovementsScreen(
          onBack: _goBack,
          onImprove: () => _goToStep(CreateFlowStep.improvementsAnalyzing),
        );

      case CreateFlowStep.improvementsAnalyzing:
        return AnalyzingScreen(
          onBack: _goBack,
          title: 'Redesigning Your Space and\nFinding Products..',
          subtitle: 'Please wait a moment while we prepare\nyour new space',
          onComplete: () => _goToStep(CreateFlowStep.dreamSpace),
        );

      case CreateFlowStep.dreamSpace:
        return DreamSpaceScreen(
          onRetry: () => _goToStep(CreateFlowStep.describeChanges),
          onRestart: () => _goToStep(CreateFlowStep.uploadPhoto),
          onHotspotTap: _goToProducts,
        );

      case CreateFlowStep.chooseProducts:
        return ChooseProductsScreen(
          hotspot: _selectedHotspot ?? const ProductHotspot(
            id: 'default',
            x: 0.5,
            y: 0.5,
            itemType: 'item',
            label: 'Product',
          ),
          onBack: () => _goToStep(CreateFlowStep.dreamSpace),
        );

      case CreateFlowStep.describeChanges:
        return DescribeChangesScreen(
          onBack: () => _goToStep(CreateFlowStep.dreamSpace),
          onContinue: () {
            // After describing changes, go back to analyzing then dream space
            _goToStep(CreateFlowStep.improvementsAnalyzing);
          },
        );
    }
  }
}
