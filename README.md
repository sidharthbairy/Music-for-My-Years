# Music-for-My-Years

"Music for My Years" is a Flask app that recommends music to the user based on their age. It creates a Spotify playlist containing the recommended songs and adds it to their account. My project uses one HTML file to prompt the user for their age. At this point, you can probably tell that the bulk of my project is backend, which is where my interest lies.

I wanted to explore the relationship between age and music taste. I looked for a dataset containing the most popular songs for different age groups. Unfortunately, I couldn't find any meaningful data. The most I could find was the preferred genres of different age groups. So naturally, I looked to generative AI for help. I found that Spotify has three metrics that they give every song on their platform – namely, danceability (how suitable a track is for dancing based on a combination of musical elements including tempo, rhythm stability, beat strength, and overall regularity), energy (a perceptual measure of intensity and activity – including dynamic range, perceived loudness, timbre, onset rate, and general entropy) and valence (the musical positiveness conveyed by a track). By varying these values, I created a recommender system.

For this project, I used two APIs – the Spotify web API and the ChatGPT API. My plan was to use ChatGPT to generate danceability, energy and valence values given a user's age. I'm aware that this isn't very accurate, but my main goal was to create a working system that runs on an innovative idea. So the program asks the user for their age, then queries the ChatGPT API with the age, getting back the three metric values.

The majority of the logic this program has involves querying the Spotify API – first, to authorise myself (the creator of the program) and obtain access and refresh tokens. Spotify requires that you make it known to the user the scope of the information you need from the user's account. The Spotify API also needs 5 "seed" tracks to recommend songs, for which I used the user's top 5 songs. So the recommendations are based on both the user's age and their top 5 tracks, allowing for greater reliability. I decided to use the "medium" time range for the user's top songs, to more accurately reflect the user's current tastes. I extensively used Python's requests library to make these HTTP requests and parse JSON responses.

The program creates a empty playlist for the user, then adds the recommended songs to it. A complication arose during the debugging phase when I had multiple playlists with the same name (i.e. the same user age) and had to make sure the songs were added to the right playlist (i.e. the newer one). I used a list of the possible playlists to counter that, selecting the first one (because Spotify adds new playlists to the start of the stack).
