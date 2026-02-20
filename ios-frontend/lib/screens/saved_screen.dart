import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/saved_space_summary.dart';
import '../providers/project_provider.dart';
import '../services/api_service.dart';
import '../services/supabase_service.dart';
import '../theme.dart';
import '../utils/logger.dart';
import 'create_flow_screen.dart';

class SavedScreen extends StatefulWidget {
  const SavedScreen({super.key});

  @override
  State<SavedScreen> createState() => _SavedScreenState();
}

class _SavedScreenState extends State<SavedScreen> {
  List<SavedSpaceSummary>? _projects;
  bool _isLoading = true;
  String? _errorMessage;
  bool _isNavigating = false;

  @override
  void initState() {
    super.initState();
    _loadProjects();
  }

  Future<void> _loadProjects() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final authToken = SupabaseService.accessToken;
      if (authToken == null) {
        setState(() {
          _isLoading = false;
          _errorMessage = 'Please sign in to view your spaces.';
        });
        return;
      }

      final response = await ApiService.getProjectSummaries(authToken);
      final projects = SavedSpaceSummary.fromProjectsResponse(response);

      if (!mounted) return;
      setState(() {
        _projects = projects;
        _isLoading = false;
      });
    } catch (e) {
      AppLogger.error('Failed to load saved spaces', e);
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to load your spaces. Pull to retry.';
      });
    }
  }

  Future<void> _onProjectTap(SavedSpaceSummary project) async {
    if (_isNavigating) return;
    setState(() => _isNavigating = true);

    try {
      final provider = Provider.of<ProjectProvider>(context, listen: false);
      final success = await provider.loadProject(project.id, context);

      if (!mounted) {
        _isNavigating = false;
        return;
      }

      if (!success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              provider.errorMessage ?? 'Failed to load project.',
            ),
            backgroundColor: AppTheme.errorColor,
          ),
        );
        setState(() => _isNavigating = false);
        return;
      }

      final step = stepForProjectStatus(project.status);
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CreateFlowScreen(startStep: step),
          fullscreenDialog: true,
        ),
      );
    } catch (e) {
      AppLogger.error('Error navigating to saved project', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isNavigating = false);
    }
  }

  Future<bool> _deleteProject(SavedSpaceSummary project) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(
          'Delete Space',
          style: AppTheme.dmSans(
            fontSize: 17,
            fontWeight: FontWeight.w600,
            color: AppTheme.bodyTextColor,
          ),
        ),
        content: Text(
          'Are you sure you want to delete "${project.displayTitle}"? This cannot be undone.',
          style: AppTheme.dmSans(
            fontSize: 14,
            color: AppTheme.textSecondary,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(
              'Cancel',
              style: AppTheme.dmSans(
                fontSize: 14,
                color: AppTheme.textSecondary,
              ),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(
              'Delete',
              style: AppTheme.dmSans(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppTheme.errorColor,
              ),
            ),
          ),
        ],
      ),
    );

    if (confirmed != true) return false;

    try {
      final authToken = SupabaseService.accessToken;
      if (authToken == null) return false;

      await ApiService.deleteProject(project.id, authToken);

      if (!mounted) return true;
      setState(() {
        _projects?.removeWhere((p) => p.id == project.id);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Space deleted',
            style: AppTheme.dmSans(fontSize: 14, color: Colors.white),
          ),
          backgroundColor: AppTheme.bodyTextColor,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      );
      return true;
    } catch (e) {
      AppLogger.error('Failed to delete project', e);
      if (!mounted) return false;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Failed to delete space. Please try again.',
            style: AppTheme.dmSans(fontSize: 14, color: Colors.white),
          ),
          backgroundColor: AppTheme.errorColor,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      );
      return false;
    }
  }

  static String _formatRelativeTime(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays == 1) return 'Yesterday';
    if (diff.inDays < 7) return '${diff.inDays} days ago';
    if (diff.inDays < 30) {
      final weeks = (diff.inDays / 7).floor();
      return weeks == 1 ? '1 week ago' : '$weeks weeks ago';
    }
    if (diff.inDays < 365) {
      final months = (diff.inDays / 30).floor();
      return months == 1 ? '1 month ago' : '$months months ago';
    }
    final years = (diff.inDays / 365).floor();
    return years == 1 ? '1 year ago' : '$years years ago';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
              child: Text(
                'Saved Spaces.',
                style: AppTheme.headerStyle(fontSize: 22),
              ),
            ),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primaryColor),
      );
    }

    if (_errorMessage != null) {
      return RefreshIndicator(
        color: AppTheme.primaryColor,
        onRefresh: _loadProjects,
        child: ListView(
          children: [
            SizedBox(
              height: MediaQuery.of(context).size.height * 0.4,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.cloud_off_rounded,
                      size: 48,
                      color: AppTheme.textTertiary,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _errorMessage!,
                      textAlign: TextAlign.center,
                      style: AppTheme.dmSans(
                        fontSize: 14,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }

    final projects = _projects;
    if (projects == null || projects.isEmpty) {
      return RefreshIndicator(
        color: AppTheme.primaryColor,
        onRefresh: _loadProjects,
        child: ListView(
          children: [
            SizedBox(
              height: MediaQuery.of(context).size.height * 0.4,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.home_outlined,
                      size: 48,
                      color: AppTheme.textTertiary,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'No saved spaces yet.\nStart a redesign to see your projects here.',
                      textAlign: TextAlign.center,
                      style: AppTheme.dmSans(
                        fontSize: 14,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      color: AppTheme.primaryColor,
      onRefresh: _loadProjects,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        itemCount: projects.length,
        itemBuilder: (context, index) {
          final project = projects[index];
          return _buildProjectCard(project);
        },
      ),
    );
  }

  Widget _buildProjectCard(SavedSpaceSummary project) {
    final imageUrl = project.displayImageUrl;

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Dismissible(
        key: Key(project.id),
        direction: DismissDirection.endToStart,
        confirmDismiss: (_) => _deleteProject(project),
        background: Container(
          alignment: Alignment.centerRight,
          padding: const EdgeInsets.only(right: 24),
          decoration: BoxDecoration(
            color: AppTheme.errorColor,
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Icon(Icons.delete_outline, color: Colors.white, size: 28),
        ),
        child: GestureDetector(
          onTap: () => _onProjectTap(project),
          child: Container(
            decoration: BoxDecoration(
              color: AppTheme.surfaceColor,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.cardBorderColor),
            ),
            clipBehavior: Clip.antiAlias,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Image section
                Stack(
                  children: [
                    SizedBox(
                      height: 200,
                      width: double.infinity,
                      child: imageUrl != null
                          ? Image.network(
                              imageUrl,
                              fit: BoxFit.cover,
                              loadingBuilder: (_, child, progress) {
                                if (progress == null) return child;
                                return Container(
                                  color: AppTheme.disabledFill,
                                  child: const Center(
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: AppTheme.primaryColor,
                                    ),
                                  ),
                                );
                              },
                              errorBuilder: (_, __, ___) => _buildPlaceholder(),
                            )
                          : _buildPlaceholder(),
                    ),
                    Positioned(
                      top: 8,
                      right: 8,
                      child: GestureDetector(
                        onTap: () => _deleteProject(project),
                        behavior: HitTestBehavior.opaque,
                        child: Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            color: Colors.black.withOpacity(0.45),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.delete_outline,
                            color: Colors.white,
                            size: 18,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                // Info section
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              project.displayTitle,
                              style: AppTheme.dmSans(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.bodyTextColor,
                              ),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              _formatRelativeTime(project.createdAt),
                              style: AppTheme.dmSans(
                                fontSize: 12,
                                color: AppTheme.grayColor,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (project.displayMode != null)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: AppTheme.selectedCardBackground,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            project.displayMode!,
                            style: AppTheme.dmSans(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.primaryColor,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPlaceholder() {
    return Container(
      color: AppTheme.disabledFill,
      child: Center(
        child: Icon(
          Icons.image_outlined,
          size: 40,
          color: AppTheme.textTertiary,
        ),
      ),
    );
  }
}
