import 'package:flutter/material.dart';
import 'package:iconsax_plus/iconsax_plus.dart';
import '../theme.dart';
import '../widgets/selectable_card.dart';

class SavedScreen extends StatelessWidget {
  const SavedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Mock Data
    final savedItems = [
      {'title': 'Living Room Fall', 'date': '2 days ago', 'image': 'assets/images/choose_space/living_room.png'},
      {'title': 'Bedroom Minimal', 'date': '1 week ago', 'image': 'assets/images/choose_space/bedroom.png'},
      {'title': 'Office Setup', 'date': '2 weeks ago', 'image': 'assets/images/choose_space/office.png'},
    ];

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Row(
                children: [
                  Text('Saved', style: AppTheme.headerStyle(fontSize: 20)),
                ],
              ),
            ),
            Expanded(
              child: GridView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  mainAxisSpacing: 16,
                  crossAxisSpacing: 16,
                  childAspectRatio: 0.75,
                ),
                itemCount: savedItems.length,
                itemBuilder: (context, index) {
                  final item = savedItems[index];
                  return SelectableCard(
                    isSelected: false,
                    onTap: () {},
                    padding: EdgeInsets.zero,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                            child: Image.asset(
                              item['image']!,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => Container(color: Colors.grey[200]),
                            ),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.all(12.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item['title']!,
                                style: const TextStyle(
                                  fontFamily: AppTheme.secondaryFont,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                  color: AppTheme.bodyTextColor,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                item['date']!,
                                style: const TextStyle(
                                  fontFamily: AppTheme.secondaryFont,
                                  fontSize: 12,
                                  color: AppTheme.grayColor,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
