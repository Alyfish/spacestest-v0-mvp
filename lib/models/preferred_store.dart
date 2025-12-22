class PreferredStore {
  final String id;
  final String name;
  final String logoUrl;

  const PreferredStore({
    required this.id,
    required this.name,
    required this.logoUrl,
  });

  factory PreferredStore.fromJson(Map<String, dynamic> json) {
    return PreferredStore(
      id: json['id'] ?? json['name'] ?? '',
      name: json['name'] ?? json['id'] ?? '',
      logoUrl: json['logoUrl'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {'id': id, 'name': name, 'logoUrl': logoUrl};
  }
}
