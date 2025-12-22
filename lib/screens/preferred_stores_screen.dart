import 'dart:math';

import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import 'package:provider/provider.dart';

import '../models/preferred_store.dart';
import '../providers/project_provider.dart';
import '../services/api_service.dart';
import '../theme.dart';
import '../widgets/custom_outlined_button.dart';
import '../widgets/icon_button.dart';

class PreferredStoresScreen extends StatelessWidget {
  final VoidCallback? onBack;
  final VoidCallback? onContinue;

  const PreferredStoresScreen({super.key, this.onBack, this.onContinue});

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
        child: PreferredStoresContent(onBack: onBack, onContinue: onContinue),
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
        currentIndex: 0,
        onTap: (_) {},
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
  int _currentPage = 0;
  late PageController _pageController;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    _loadStores();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _loadStores() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final stores = await ApiService.fetchPreferredStores();
      final projectProvider = Provider.of<ProjectProvider>(
        context,
        listen: false,
      );
      final existingSelection = projectProvider.preferredStores;

      setState(() {
        _stores = stores;
        _selectedStoreIds = existingSelection.isNotEmpty
            ? existingSelection.toSet()
            : {};
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Could not load stores. Pull to retry later.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  List<List<PreferredStore>> get _storePages {
    if (_stores.isEmpty) return [];

    final List<List<PreferredStore>> pages = [];
    for (int i = 0; i < _stores.length; i += 4) {
      pages.add(_stores.sublist(i, min(i + 4, _stores.length)));
    }
    return pages;
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

    final projectProvider = Provider.of<ProjectProvider>(
      context,
      listen: false,
    );

    if (!projectProvider.hasProject) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Create a project before selecting stores'),
          backgroundColor: AppTheme.errorColor,
        ),
      );
      return;
    }

    setState(() {
      _isSaving = true;
    });

    final success = await projectProvider.savePreferredStores(
      context,
      _selectedStoreIds.toList(),
    );

    if (mounted) {
      setState(() {
        _isSaving = false;
      });

      if (success) {
        if (widget.onContinue != null) {
          widget.onContinue!();
        }
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Couldn't save your selection"),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  void _onContinueTap() {
    _handleContinue();
  }

  Widget _buildStoreCard(PreferredStore store) {
    final isSelected = _selectedStoreIds.contains(store.id);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: isSelected
          ? AppTheme.selectedCardDecoration
          : AppTheme.unselectedCardDecoration,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _toggleSelection(store.id),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: AppTheme.backgroundColor,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.network(
                      store.logoUrl,
                      fit: BoxFit.contain,
                      errorBuilder: (context, error, stackTrace) {
                        return Container(
                          alignment: Alignment.center,
                          color: AppTheme.grayColor.withValues(alpha: 0.1),
                          child: Icon(
                            IconsaxPlusLinear.image,
                            color: AppTheme.grayColor,
                            size: 32,
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                store.name,
                style: TextStyle(
                  fontFamily: AppTheme.secondaryFont,
                  fontSize: 16,
                  fontWeight: FontWeight.w400,
                  color: isSelected
                      ? AppTheme.selectedCardOutline
                      : AppTheme.grayColor,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 80),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (_errorMessage != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 40),
        child: Column(
          children: [
            Text(
              _errorMessage!,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: AppTheme.secondaryFont,
                fontSize: 16,
                color: AppTheme.grayColor,
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton(onPressed: _loadStores, child: const Text('Retry')),
          ],
        ),
      );
    }

    if (_storePages.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 60),
        child: Column(
          children: [
            Icon(IconsaxPlusLinear.box_remove, color: AppTheme.grayColor),
            const SizedBox(height: 12),
            Text(
              'No stores available right now',
              style: TextStyle(
                fontFamily: AppTheme.secondaryFont,
                fontSize: 16,
                color: AppTheme.grayColor,
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        SizedBox(
          height: MediaQuery.of(context).size.height * 0.55,
          child: PageView.builder(
            controller: _pageController,
            itemCount: _storePages.length,
            onPageChanged: (index) {
              setState(() {
                _currentPage = index;
              });
            },
            itemBuilder: (context, index) {
              final pageStores = _storePages[index];
              return _buildStoreGrid(pageStores);
            },
          ),
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(
            _storePages.length,
            (index) => Container(
              margin: const EdgeInsets.symmetric(horizontal: 4),
              width: _currentPage == index ? 12 : 8,
              height: 8,
              decoration: BoxDecoration(
                color: _currentPage == index
                    ? AppTheme.primaryColor
                    : AppTheme.grayColor.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(6),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStoreGrid(List<PreferredStore> stores) {
    return GridView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 16,
        crossAxisSpacing: 16,
        childAspectRatio: 0.82,
      ),
      itemCount: stores.length,
      physics: const NeverScrollableScrollPhysics(),
      itemBuilder: (context, index) {
        return _buildStoreCard(stores[index]);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _loadStores,
      color: AppTheme.primaryColor,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 12.0),
        child: Column(
          children: [
            Row(
              children: const [
                Text('Preferred Store(s).', style: AppTheme.sectionTitleStyle),
              ],
            ),
            const SizedBox(height: 20),
            _buildContent(),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButtonWidget(
                  onPressed: widget.onBack ?? () => Navigator.pop(context),
                  icon: IconsaxPlusLinear.arrow_left_2,
                ),
                const SizedBox(width: 16),
                CustomOutlinedButton(
                  text: _isSaving ? 'Saving...' : 'Continue',
                  icon: IconsaxPlusLinear.arrow_right_2,
                  onPressed: _isSaving ? () {} : _onContinueTap,
                  textColor: AppTheme.bodyTextColor,
                  borderColor: AppTheme.primaryColor,
                  iconColor: AppTheme.primaryColor,
                ),
              ],
            ),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
  }
}
