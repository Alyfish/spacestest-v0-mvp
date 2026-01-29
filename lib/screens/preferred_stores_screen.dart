import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/preferred_store.dart';
import '../providers/project_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/step_progress_bar.dart';

class PreferredStoresScreen extends StatelessWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const PreferredStoresScreen({super.key, this.onBack, this.onContinue});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.scaffoldBackground,
      body: SafeArea(
        child: PreferredStoresContent(onBack: onBack, onContinue: onContinue),
      ),
    );
  }
}

class PreferredStoresContent extends StatefulWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const PreferredStoresContent({super.key, this.onBack, this.onContinue});

  @override
  State<PreferredStoresContent> createState() => _PreferredStoresContentState();
}

class _PreferredStoresContentState extends State<PreferredStoresContent> {
  bool _isLoading = true;
  bool _isSaving = false;
  String? _errorMessage;
  List<PreferredStore> _stores = [];
  Set<String> _selectedStoreIds = {};

  @override
  void initState() {
    super.initState();
    _loadStores();
  }

  Future<void> _loadStores() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final stores = await ApiService.fetchPreferredStores();
      final projectProvider =
          Provider.of<ProjectProvider>(context, listen: false);
      final existingSelection = projectProvider.preferredStores;
      setState(() {
        _stores = stores;
        _selectedStoreIds =
            existingSelection.isNotEmpty ? existingSelection.toSet() : {};
      });
    } catch (e) {
      setState(() => _errorMessage = 'Could not load stores.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _toggleSelection(String storeId) {
    setState(() {
      if (_selectedStoreIds.contains(storeId)) {
        _selectedStoreIds.remove(storeId);
      } else {
        _selectedStoreIds.add(storeId);
      }
    });
  }

  Future<void> _handleContinue() async {
    if (_isSaving || _isLoading) return;
    final projectProvider =
        Provider.of<ProjectProvider>(context, listen: false);

    if (!projectProvider.hasProject) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Create a project first',
            style: AppTheme.dmSans(color: Colors.white),
          ),
          backgroundColor: AppTheme.errorColor,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);
    final success = await projectProvider.savePreferredStores(
        context, _selectedStoreIds.toList());

    if (mounted) {
      setState(() => _isSaving = false);
      if (success) widget.onContinue?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header with logo and settings
        _buildHeader(),

        // Progress bar
        const SizedBox(height: 8),
        const StepProgressBar(currentStep: 6, totalSteps: 8),

        // Content
        Expanded(
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _errorMessage != null
                  ? _buildErrorState()
                  : SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SizedBox(height: 24),

                          // Title
                          Text(
                            'Preferred Store(s).',
                            style: AppTheme.dmSans(
                              fontSize: 26,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.textPrimary,
                            ),
                          ),

                          const SizedBox(height: 24),

                          // Stores grid
                          _buildStoresGrid(),

                          const SizedBox(height: 100),
                        ],
                      ),
                    ),
        ),

        // Bottom Buttons
        _buildBottomButtons(),
      ],
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Spaces. logo
          Image.asset(
            'assets/logo/logo.png',
            height: 32,
          ),
          // Settings icon
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: AppTheme.dividerColor,
                width: 1,
              ),
            ),
            child: IconButton(
              icon: const Icon(
                Icons.settings_outlined,
                color: AppTheme.textPrimary,
                size: 22,
              ),
              onPressed: () {},
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            _errorMessage!,
            style: AppTheme.dmSans(
              fontSize: 16,
              color: AppTheme.textSecondary,
            ),
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: _loadStores,
            child: Text(
              'Retry',
              style: AppTheme.dmSans(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: AppTheme.primaryColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStoresGrid() {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 16,
        crossAxisSpacing: 16,
        childAspectRatio: 1.0,
      ),
      itemCount: _stores.length,
      itemBuilder: (context, index) {
        final store = _stores[index];
        final isSelected = _selectedStoreIds.contains(store.id);

        return _buildStoreCard(store, isSelected);
      },
    );
  }

  Widget _buildStoreCard(PreferredStore store, bool isSelected) {
    return GestureDetector(
      onTap: () => _toggleSelection(store.id),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? AppTheme.primaryColor : AppTheme.dividerColor,
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Store logo - supports both local assets and network URLs
            SizedBox(
              height: 60,
              child: store.logoUrl.isNotEmpty
                  ? (store.logoUrl.startsWith('assets/')
                      ? Image.asset(
                          store.logoUrl,
                          fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => _buildFallbackLogo(),
                        )
                      : Image.network(
                          store.logoUrl,
                          fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => _buildFallbackLogo(),
                        ))
                  : _buildFallbackLogo(),
            ),

            const SizedBox(height: 12),

            // Store name
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Text(
                store.name,
                style: AppTheme.dmSans(
                  fontSize: 14,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  color: isSelected ? AppTheme.primaryColor : AppTheme.textPrimary,
                ),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFallbackLogo() {
    return Container(
      width: 60,
      height: 60,
      decoration: BoxDecoration(
        color: AppTheme.scaffoldBackground,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(
        Icons.store_outlined,
        size: 32,
        color: AppTheme.textTertiary,
      ),
    );
  }

  Widget _buildBottomButtons() {
    final hasSelection = _selectedStoreIds.isNotEmpty;

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
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
        child: Row(
          children: [
            // Back button
            Expanded(
              child: SizedBox(
                height: 56,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.textPrimary,
                    side:
                        const BorderSide(color: AppTheme.dividerColor, width: 1.5),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  onPressed: widget.onBack,
                  child: Text(
                    'Back',
                    style: AppTheme.dmSans(
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ),
              ),
            ),

            const SizedBox(width: 12),

            // Skip/Continue button - changes based on selection
            Expanded(
              child: SizedBox(
                height: 56,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryColor,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  onPressed: _isSaving ? null : _handleContinue,
                  child: _isSaving
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Colors.white,
                          ),
                        )
                      : Text(
                          hasSelection ? 'Continue' : 'Skip',
                          style: AppTheme.dmSans(
                            fontSize: 17,
                            fontWeight: FontWeight.w600,
                            color: Colors.white,
                          ),
                        ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
