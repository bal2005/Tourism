import os
import json
import datetime
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from bard import generate_itinerary  # Import Bard itinerary generator function
import requests  # For the weather API

# Initialize Flask app
app = Flask(__name__)

# API Keys
weather_api_key = "JG9QU6FJ4Q4QEVHMYDHTDDV5B"  # Visual Crossing Weather API Key
bard_api_key = "AIzaSyD7CcYRXcznLWaP4LrK0Ghe6tIVhod4j2o"  # Bard API Key

# Secret key for flash messages
app.secret_key = "your_secret_key"

# Directory for storing uploaded guide photos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to validate file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Local Guide Data Storage
guides_data_file = 'guides.json'

# Load existing local guide data
def load_guides():
    if os.path.exists(guides_data_file):
        with open(guides_data_file, 'r') as f:
            return json.load(f)
    return []

# Save updated local guide data
def save_guides(guides):
    with open(guides_data_file, 'w') as f:
        json.dump(guides, f, indent=4)

# Weather API Function
def get_weather_data(api_key, location, start_date, end_date):
    base_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/{start_date}/{end_date}?unitGroup=metric&include=days&key={api_key}&contentType=json"

    try:
        response = requests.get(base_url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        return None

# Route: Home
@app.route('/')
def home():
    return render_template('index.html')

# Route: About
@app.route('/about')
def about():
    return render_template('about.html')

# Route: City - Handles form submission and displays itinerary
@app.route('/city', methods=["GET", "POST"])
def city():
    if request.method == "POST":
        # Fetch user inputs
        source = request.form.get("source")
        destination = request.form.get("destination")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        # Calculate the number of days
        try:
            no_of_days = (datetime.datetime.strptime(end_date, "%Y-%m-%d") - 
                          datetime.datetime.strptime(start_date, "%Y-%m-%d")).days
        except Exception as e:
            flash("Invalid date format. Please use YYYY-MM-DD.", "error")
            return redirect(url_for('city'))

        # Validate all inputs
        if not all([source, destination, start_date, end_date]) or no_of_days <= 0:
            flash("Please fill in all fields correctly.", "error")
            return redirect(url_for('city'))

        try:
            # Fetch weather data
            weather_data = get_weather_data(weather_api_key, destination, start_date, end_date)

            # Generate itinerary using Bard API
            itinerary = generate_itinerary(source, destination, start_date, end_date, no_of_days)

            return render_template(
                'city.html',
                itinerary=itinerary,
                weather_data=weather_data,
                source=source,
                destination=destination,
                start_date=start_date,
                end_date=end_date
            )

        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('city'))

    return render_template('city.html', itinerary=None, weather_data=None)

# Route: Destinations
@app.route('/destinations')
def destinations():
    return render_template('destinations.html')

# Route: Local Guide (GET and POST for adding guides)
@app.route('/local_guide', methods=["GET", "POST"])
def local_guide():
    guides = load_guides()  # Load existing guides

    if request.method == "POST":
        # Fetch form data
        name = request.form.get("name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        years_experience = request.form.get("years_experience")
        city = request.form.get("city")
        city_condition = request.form.get("city_condition")
        photo = request.files.get("photo")

        # Validate form data
        if not all([name, age, gender, years_experience, city, city_condition, photo]):
            flash("All fields are required.", "error")
            return redirect(url_for('local_guide'))

        if not allowed_file(photo.filename):
            flash("Invalid file type. Allowed types: png, jpg, jpeg, gif.", "error")
            return redirect(url_for('local_guide'))

        # Save uploaded photo
        filename = secure_filename(photo.filename)
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)

        # Add guide data to the list
        new_guide = {
            "name": name,
            "age": age,
            "gender": gender,
            "years_experience": years_experience,
            "city": city,
            "photo": photo_path,
            "city_condition": city_condition
        }
        guides.append(new_guide)
        save_guides(guides)  # Save updated guides

        flash("Local guide added successfully!", "success")
        return redirect(url_for('local_guide'))

    return render_template('local_guide.html', guides=guides)

@app.route('/update_city_condition/<guide_id>', methods=['POST'])
def update_city_condition(guide_id):
    city_condition = request.form.get('city_condition')
    update_guide_city_condition(guide_id, city_condition)
    flash('City condition updated successfully!', 'success')
    return redirect(url_for('local_guide'))


# Route: Details for zones
@app.route('/details/<zone>')
def details(zone):
    with open('zones.json') as f:
        zones_data = json.load(f)
    
    zone_data = zones_data.get(zone)
    if not zone_data:
        return "Zone not found", 404

    return render_template('details.html', zone=zone, zone_data=zone_data)

# Route: Weather for a specific city (newly added)
@app.route('/weather/<city>')
def weather(city):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    weather_data = get_weather_data(weather_api_key, city, today, tomorrow)
    if not weather_data:
        flash(f"Weather data for {city} could not be retrieved.", "error")
        return redirect(url_for('city'))
    
    return render_template('weather.html', city=city, weather_data=weather_data)

# Error handler for 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Run the application
if __name__ == '__main__':
    # Ensure the upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
