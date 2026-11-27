# Gradient Generator
Gradient Generator is a Django-based web application and REST API that allows users to create CSS linear gradients with customizable or random colors. The project features a user-friendly web interface for interactive gradient creation and a REST API for programmatic access, with OpenAPI documentation powered by drf-spectacular.

## Features
### Web Interface:
- Interactive gradient preview with a side-by-side layout (gradient box on the left, controls on the right).
- Supports two to six color inputs for creating complex gradients.
- Linear, radial and conic gradients, with an angle slider (0–360°) for linear and conic ones. The preview follows the controls live, and the style is kept in the URL (`?type=conic&angle=45`).
- CSS Color 4 colour interpolation: sRGB (classic), OKLab, OKLCH or HSL longer hue (a rainbow sweep the long way round the colour wheel), e.g. `linear-gradient(90deg in oklch, …)`. Kept in the URL as `?interpolation=oklch`.
- Easing curves: Linear, Ease-In-Out (CSS `cubic-bezier(0.42, 0, 0.58, 1)`) or Smoothstep (`3t² − 2t³`). Anything but linear injects 6 evenly spaced stops between each pair of colours, coloured along the curve in the chosen interpolation space, for softer, more natural light falloffs. Kept in the URL as `?easing=smoothstep`.
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
- Pick Linear, Radial or Conic, and drag the angle slider (linear and conic).
- Click "Random Colors" to generate a new random gradient.
- Click "Update Gradient" to apply custom selections.
- Copy the CSS code from the textarea manually.

### REST API
#### GET /api/gradient/
Returns one gradient (JSON by default). Query parameters:
  - type: `linear` (default), `radial` or `conic`.
  - direction: `to top`, `to right`, `to bottom`, `to left`, a corner such as `to top right`, or an angle from `-360deg` to `360deg`. Default: `to top`. For conic gradients it is the start angle; radial ones ignore it.
  - interpolation: `srgb` (default, no clause), `oklab`, `oklch` or `hsl-longer` (`in hsl longer hue`). SVG output draws the non-sRGB ones with extra colour stops sampled in that space.
  - easing: `linear` (default), `ease-in-out` or `smoothstep`. Anything but linear adds 6 eased stops (with positions) between each pair of colours.
  - count: number of colours, 2–6. Given colours are blended or sampled to that many.
  - color1 to color6: Hex color codes (e.g., #ff0000). Defaults to random colors if not provided.
  - random: Set to true to generate random colors (ignores color1 to color6, except slots kept with `lock=1,3`).
  - format: `json` (default), `css` (the CSS declaration as `text/css`) or `svg` (a 400×400 SVG image; not for conic gradients, which SVG cannot draw). An `Accept` header works too.

An invalid `type`, `direction`, `interpolation`, `easing` or `count` returns 400 with the error as JSON.

#### POST /api/gradient/
Saves `color1`…`colorN` (and an optional `name`) as a palette. Requires login, and is limited per user
(default 30 per hour; set `PALETTE_CREATE_RATE`, e.g. `100/day`). Over the limit it returns 429 with a `Retry-After` header.

#### GET /api/palettes/
Saved palettes, oldest first, 20 per page: `?page=2`, `?page_size=` (up to 100), `?mine=true` for your own (requires login).

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

**Live Demo:** [https://generate-gradients.onrender.com](https://generate-gradients.onrender.com)
Note: Hosted on Render's free tier. If the link takes ~30 seconds to load initially, it is waking up the server instance.
