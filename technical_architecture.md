# Technical Architecture & Rules

## Core Features
This application provides an AI-powered interior design workflow involving:
1. **Space Analysis**: Uploading and analyzing base room images.
2. **Context Gathering**: Selecting space type, color palette, design style, and preferred stores.
3. **Recommendation Generation**: Two parallel flows for generating actionable design changes:
    - **Inspiration Recommendations**: Derived from user-uploaded inspiration images.
    - **Product Recommendations**: Derived from global style/color context and improvement markers.
4. **Product Search & Visualization**: Searching for real products based on recommendations and generating a final visualized image.

## Critical Rules
> [!IMPORTANT]
> **PRESERVATION OF FLOW COMPONENTS**
> 
> The following components are CRITICAL to the user journey and must **NEVER** be removed, hidden, or disabled without explicit user authorization:
> 
> 1.  **`InspirationRecommendations.tsx`**: The interface for generating and selecting inspiration-based ideas.
> 2.  **`ProductRecommendations.tsx`**: The interface for generating and selecting marker/style-based ideas.
> 3.  **`ProductSearchResults.tsx`**: The engine for searching real products based on the selected recommendation.
>
> **The Flow Requirement:**
> The application MUST always support the complete flow:
> `Generate Recommendations` -> `Select Recommendation` -> `Find/Search Products`
>
> This flow must work for BOTH Inspiration-based and Standard recommendations.

### Recommendation Generation System

The application generates exactly 6 recommendations through three distinct paths, ensuring the user always has a clear, actionable path forward.

### Core Logic & Constraints
- **Quantity**: Always exactly 6 recommendations.
- **Constraints**: 2-4 words for product recommendations; 1-2 sentences for marker/inspiration recommendations.
- **Goal**: Provide high-impact, realistic, and complementary design changes.

### Path 1: Marker-Based Recommendations
**Trigger**: Automatically generated after the user saves "Improvement Markers" on the image.
- **User Inputs & Factors**:
    - **Space Type**: Contextualizes the room (e.g., Living Room vs. Bedroom).
    - **Improvement Markers**: Detailed descriptions and spatial coordinates (X, Y) provided by the user.
    - **Labelled Image**: Vision API analyzes the original image with markers overlaid.
    - **Style/Color (if available)**: Incorporates user preferences if already selected.
    - **Preferred Stores**: Retailers to prioritize in recommendations.
- **System Prompt Fragment**: *"You are an expert interior designer... Provide specific, actionable recommendations for improving spaces based on user feedback. Focus on practical changes... always return exactly 6 recommendations."*

### Path 2: Inspiration-Based Recommendations
**Trigger**: Generated when user uploads inspiration images.
- **User Inputs & Factors**:
    - **Base Image vs. Inspiration Images**: Visual analysis comparing the current room to the desired look.
    - **Space Type**: Ensures consistency with room purpose.
    - **Style & Color Analysis**: Deep context from the Style/Color Agent results.
    - **Preferred Stores & Markers**: User-specific constraints and retailer preferences.
- **System Prompt Fragment**: *"Analyze the attached base room image along with the inspiration images... provide exactly 6 specific recommendations."*

### Path 3: Actionable Product Recommendations
**Trigger**: Final stage before product search, synthesizing all project context.
- **User Inputs & Factors**:
    - **Full Project Context**: Combines Space Type, Room Status (Empty/Furnished), Improvement Markers (descriptions + coordinates), Color Analysis (Primary/Palette/Lighting), Style Analysis (Style/Materials/Characteristics), and any Inspiration recommendations.
- **System Prompt Fragment**: *"Based on this comprehensive interior design project context, generate exactly 6 specific, actionable product recommendations... Each recommendation should be a specific action (e.g., 'change sofa', 'add coffee table')."*

### Synthesis & Priority Logic
When both markers and inspiration images exist, the system handles them as follows:

1.  **Marker Priority**: Improvement markers are treated as "High Priority User Requests". In all recommendation paths, the AI is explicitly told to prioritize these specific spatial areas.
2.  **Visual Context matching**: Inspiration images provide the "Visual Target" (the look), while markers provide the "Functional Target" (the fix).
3.  **Synthesis Layer**: The final `Product Recommendations` step acts as a synthesis engine. It reads the specific ideas generated from inspiration images AND the specific fixes requested via markers to produce a singular, cohesive set of 4 actionable items.
4.  **UI Representation**:
    *   **Phase-Specific**: Users see initial ideas based on markers early on.
    *   **Inspiration-Specific**: If they provide inspiration, they see a separate list that merges inspiration with their markers.
    *   **Unified Final List**: The ultimate goal is to reach the unified `Product Recommendations` section which represents the best outcome of all inputs combined.

---

## Component Interactions
- **Selection Logic**: Both `InspirationRecommendations` and `ProductRecommendations` feed into the same `selected_product_recommendations` context field.
- **Search Trigger**: `ProductSearchResults` monitors `selected_product_recommendations`. When a recommendation is selected (status `PRODUCT_RECOMMENDATION_SELECTED`), this component becomes active to allow product searching.

