# Gradient Generator
Gradient Generator is a Django-based web application and REST API that allows users to create CSS linear gradients with customizable or random colors. The project features a user-friendly web interface for interactive gradient creation and a REST API for programmatic access, with OpenAPI documentation powered by drf-spectacular.

## Features
### Web Interface:
- Interactive gradient preview with a side-by-side layout (gradient box on the left, controls on the right).
- Supports six color inputs for creating complex gradients.
- Allows selection of gradient direction (to right, to left, to bottom, to top).
- Option to generate random colors for quick experimentation.
- Displays the generated CSS code for manual copying.
- Fully server-side, no JavaScript required.

### REST API:
- Endpoint (/api/gradient/) to generate gradients programmatically.
- Supports custom colors, direction, and random color generation via query parameters.
- Returns JSON with gradient details and CSS code.
- Interactive API documentation via Swagger UI and ReDoc, powered by drf-spectacular.

## Installation

### Prerequisites
Python 3.8+
Git
Virtualenv (recommended)
Setup
## Usage
### Web Interface
- Access: http://127.0.0.1:8000/gradient/
### Features:
- Use the color pickers to select up to six colors.
- Choose a gradient direction from the dropdown.
- Click "Random Colors" to generate a new random gradient.
- Click "Update Gradient" to apply custom selections.
- Copy the CSS code from the textarea manually.

### REST API
- Endpoint: http://127.0.0.1:8000/api/gradient/
- Query Parameters:
  - direction: Gradient direction (e.g., to right, to left, to bottom, to top). Default: to right.
  - color1 to color6: Hex color codes (e.g., #ff0000). Defaults to random colors if not provided. 
  - random: Set to true to generate random colors (ignores color1 to color6).

### API Documentation:
- Swagger UI: http://127.0.0.1:8000/api/schema/swagger-ui/
- ReDoc: http://127.0.0.1:8000/api/schema/redoc/

## Project Structure
- views.py: Handles web interface (generate_gradient) and API (GradientAPIView).
- forms.py: Defines GradientForm for input validation (direction and colors).
- serializers.py: Defines GradientSerializer for API response structure.
- urls.py: Configures routes for web interface, API, and documentation.
- style.css: Styles the web interface with a 2:1 layout (gradient box twice as wide as controls).
- index.html: Renders the web interface using Django Template Language.

## Contributing
Contributions are welcome! Please:
1. Fork the repository.
2. Create a feature branch (git checkout -b feature/your-feature).
3. Commit changes (git commit -m "Add your feature").
4. Push to the branch (git push origin feature/your-feature).
5. Open a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Contact
For questions or feedback, reach out via GitHub Issues or contact sdplamen@gmail.com.