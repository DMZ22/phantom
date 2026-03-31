import random
import re

# Offline movie expert chatbot — no API needed

GREETINGS = [
    "Hey there, movie buff! What are you in the mood for today?",
    "Welcome to Phantom! Ask me anything about movies — genres, recommendations, trivia, you name it.",
    "Hey! I'm Phantom, your movie expert. What do you want to watch tonight?",
]

GENRE_RECOMMENDATIONS = {
    "sci-fi": {
        "movies": ["Interstellar", "Blade Runner 2049", "Arrival", "The Matrix", "Inception", "Dune", "Ex Machina", "2001: A Space Odyssey", "Alien", "The Martian"],
        "response": "Sci-fi is my jam! Here are some must-watches:\n\n{movies}\n\nIf you want mind-bending, go **Interstellar** or **Arrival**. Want action? **The Matrix** never gets old. For something slower and gorgeous, **Blade Runner 2049** is a visual masterpiece.",
    },
    "horror": {
        "movies": ["Hereditary", "The Shining", "Get Out", "A Quiet Place", "The Conjuring", "Midsommar", "It Follows", "The Exorcist", "Scream", "28 Days Later"],
        "response": "Oh you like being scared? Excellent taste.\n\n{movies}\n\n**Hereditary** will genuinely mess you up — Toni Collette deserved every award. **Get Out** is horror meets social commentary at its finest. And if you want a classic, **The Shining** is Kubrick at his most unsettling.",
    },
    "comedy": {
        "movies": ["Superbad", "The Grand Budapest Hotel", "Bridesmaids", "Step Brothers", "The Big Lebowski", "Parasite", "Knives Out", "The Hangover", "Airplane!", "Monty Python and the Holy Grail"],
        "response": "Need a good laugh? Say no more!\n\n{movies}\n\n**The Grand Budapest Hotel** is Wes Anderson perfection. **Superbad** is peak coming-of-age comedy. And honestly, **The Big Lebowski** just gets funnier every time you watch it. The Dude abides.",
    },
    "action": {
        "movies": ["Mad Max: Fury Road", "John Wick", "Die Hard", "The Dark Knight", "Mission: Impossible - Fallout", "Kill Bill", "Top Gun: Maverick", "Gladiator", "The Raid", "Terminator 2"],
        "response": "Action movies? Let's get your adrenaline pumping!\n\n{movies}\n\n**Mad Max: Fury Road** is basically a 2-hour car chase and it's PERFECT. **John Wick** made Keanu Reeves an action god again. And **The Dark Knight** — Heath Ledger's Joker is still the gold standard.",
    },
    "romance": {
        "movies": ["Before Sunrise", "The Notebook", "Eternal Sunshine of the Spotless Mind", "Pride and Prejudice", "La La Land", "When Harry Met Sally", "500 Days of Summer", "Titanic", "Call Me by Your Name", "About Time"],
        "response": "Feeling romantic? I've got you covered!\n\n{movies}\n\n**Before Sunrise** is the most authentic romance ever filmed — just two people talking in Vienna. **Eternal Sunshine** will break your heart and put it back together. And **La La Land** proves musicals aren't dead.",
    },
    "thriller": {
        "movies": ["Se7en", "Gone Girl", "Prisoners", "Zodiac", "No Country for Old Men", "Shutter Island", "Sicario", "The Silence of the Lambs", "Nightcrawler", "Oldboy"],
        "response": "Thrillers that'll keep you on the edge of your seat:\n\n{movies}\n\n**Gone Girl** has the best plot twist of the century — Rosamund Pike is terrifying. **Prisoners** is an underrated masterpiece by Villeneuve. And **Se7en** — that ending still haunts me.",
    },
    "animation": {
        "movies": ["Spider-Man: Into the Spider-Verse", "Spirited Away", "The Lion King", "WALL-E", "Coco", "Your Name", "Toy Story", "Ratatouille", "Akira", "Princess Mononoke"],
        "response": "Animation isn't just for kids — it's an art form!\n\n{movies}\n\n**Spider-Verse** literally redefined what animation could be. **Spirited Away** is Miyazaki's masterpiece (fight me). And **WALL-E** tells a better love story in silence than most movies do with dialogue.",
    },
    "drama": {
        "movies": ["The Shawshank Redemption", "Forrest Gump", "Schindler's List", "Fight Club", "The Godfather", "Whiplash", "12 Angry Men", "Good Will Hunting", "The Pursuit of Happyness", "A Beautiful Mind"],
        "response": "Drama — where cinema truly shines:\n\n{movies}\n\n**Shawshank** is the greatest film ever made, and I will die on that hill. **Whiplash** will make your palms sweat — J.K. Simmons is INTENSE. And **The Godfather**... I mean, it's an offer you can't refuse.",
    },
    "bollywood": {
        "movies": ["3 Idiots", "Dangal", "Lagaan", "Dil Chahta Hai", "Gangs of Wasseypur", "Andhadhun", "Tumbbad", "Rang De Basanti", "Zindagi Na Milegi Dobara", "Barfi!"],
        "response": "Bollywood has some absolute gems!\n\n{movies}\n\n**3 Idiots** is a perfect blend of comedy and heart — Aamir Khan at his best. **Gangs of Wasseypur** is India's answer to The Godfather. And **Tumbbad** — if you haven't seen this horror masterpiece, drop everything and watch it NOW.",
    },
}

TRIVIA = [
    "Did you know? The chest-burster scene in **Alien** (1979) wasn't rehearsed — the cast's horrified reactions were genuine!",
    "Fun fact: **The Shining**'s iconic 'Here's Johnny!' was improvised by Jack Nicholson. Kubrick kept it despite the line not being in the script.",
    "Movie trivia: In **Fight Club**, Tyler Durden flashes on screen 4 times before he's officially introduced. Blink and you'll miss it!",
    "Did you know? **Mad Max: Fury Road** used over 150 real vehicles and minimal CGI for the stunts. Pure practical effects madness!",
    "Fun fact: Heath Ledger locked himself in a hotel room for 6 weeks to develop his Joker character in **The Dark Knight**.",
    "Trivia time: **Parasite** (2019) was the first non-English language film to win Best Picture at the Oscars!",
    "Did you know? The sound of the velociraptors in **Jurassic Park** was made by recording tortoises mating. I'm not kidding.",
    "Fun fact: **Inception**'s hallway fight scene was filmed in a rotating set — Joseph Gordon-Levitt trained for weeks to pull it off!",
    "Movie trivia: In **The Matrix**, all the code raining down the screen is actually sushi recipes in Japanese!",
    "Did you know? **Titanic** cost more to make ($200M in 1997) than the actual Titanic ship cost to build ($7.5M in 1912, ~$190M adjusted)!",
    "Fun fact: **Toy Story** (1995) was the first fully computer-animated feature film ever made. Pixar changed the game forever.",
    "Trivia: **The Godfather**'s cat wasn't in the script — it was a stray that wandered on set, and Marlon Brando just picked it up!",
    "Did you know? **Interstellar**'s black hole visualization was so accurate that it led to a published scientific paper!",
    "Fun fact: **Django Unchained** — Leonardo DiCaprio actually cut his hand on a glass during a scene and kept acting. The blood is real!",
    "Movie trivia: **Psycho** (1960) was the first American film to show a toilet being flushed on screen. Hitchcock was a rebel!",
]

DIRECTOR_RECS = {
    "nolan": "Christopher Nolan is a master of mind-bending cinema! Must-watch order: **Memento** (his breakout), **The Dark Knight** (superhero perfection), **Inception** (dream heist), **Interstellar** (space + emotions), **Oppenheimer** (his magnum opus). Every frame is deliberate.",
    "tarantino": "Tarantino's filmography is a masterclass in dialogue and style! Start with **Pulp Fiction**, then **Kill Bill**, **Inglourious Basterds**, **Django Unchained**, and **Once Upon a Time in Hollywood**. Nobody writes dialogue like this man.",
    "kubrick": "Stanley Kubrick was a perfectionist genius. **2001: A Space Odyssey** (revolutionary), **The Shining** (terrifying), **A Clockwork Orange** (disturbing), **Full Metal Jacket** (war horror). Every film is a cinematic event.",
    "scorsese": "Scorsese is the GOAT of gangster films. **Goodfellas** (perfect), **Taxi Driver** (iconic), **The Departed** (finally got his Oscar), **The Wolf of Wall Street** (wild ride), **Killers of the Flower Moon** (his latest masterpiece).",
    "spielberg": "Spielberg literally defined modern blockbusters. **Jaws** (invented summer movies), **Schindler's List** (devastating), **Jurassic Park** (changed VFX forever), **Saving Private Ryan** (brutal opening), **Raiders of the Lost Ark** (pure adventure).",
    "villeneuve": "Denis Villeneuve is the best director working today, fight me. **Arrival** (brainy sci-fi), **Blade Runner 2049** (gorgeous), **Sicario** (tense AF), **Dune** (epic), **Prisoners** (underrated thriller). The man doesn't miss.",
    "miyazaki": "Hayao Miyazaki is the Walt Disney of anime. **Spirited Away** (Oscar-winning masterpiece), **Princess Mononoke** (epic), **My Neighbor Totoro** (pure joy), **Howl's Moving Castle** (romantic), **The Wind Rises** (beautiful swan song... or so we thought).",
}

FALLBACK_RESPONSES = [
    "Hmm, that's a great question! I'm better at recommending movies though. Try asking me for sci-fi, horror, comedy, action, or any genre recommendations!",
    "I'm all about movies! Ask me for recommendations by genre, director picks, or just say 'trivia' for a fun movie fact!",
    "Not sure about that one, but I can talk movies all day! Try asking: 'recommend me a thriller' or 'tell me about Nolan's films' or just say 'surprise me'!",
    "That's outside my projector range! But ask me about any movie genre, director, or just say 'trivia' and I'll blow your mind with movie facts.",
]


def _format_movie_list(movies):
    return "\n".join(f"  - **{m}**" for m in movies)


def _detect_genre(text):
    text_lower = text.lower()
    genre_keywords = {
        "sci-fi": ["sci-fi", "sci fi", "science fiction", "space", "futuristic", "cyberpunk"],
        "horror": ["horror", "scary", "spooky", "creepy", "terrifying", "ghost", "haunted"],
        "comedy": ["comedy", "funny", "laugh", "hilarious", "humor", "humour"],
        "action": ["action", "fight", "explosion", "adrenaline", "stunts", "martial arts"],
        "romance": ["romance", "romantic", "love story", "love", "relationship", "rom-com", "romcom"],
        "thriller": ["thriller", "suspense", "mystery", "tense", "detective", "crime"],
        "animation": ["animation", "animated", "anime", "cartoon", "pixar", "ghibli", "disney"],
        "drama": ["drama", "dramatic", "emotional", "intense", "serious"],
        "bollywood": ["bollywood", "hindi", "indian movie", "desi"],
    }
    for genre, keywords in genre_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                return genre
    return None


def _detect_director(text):
    text_lower = text.lower()
    for key in DIRECTOR_RECS:
        if key in text_lower:
            return key
    # Full name matches
    name_map = {
        "christopher nolan": "nolan", "chris nolan": "nolan",
        "quentin tarantino": "tarantino",
        "stanley kubrick": "kubrick",
        "martin scorsese": "scorsese",
        "steven spielberg": "spielberg",
        "denis villeneuve": "villeneuve",
        "hayao miyazaki": "miyazaki",
    }
    for name, key in name_map.items():
        if name in text_lower:
            return key
    return None


class ChatService:
    def chat(self, movie_id, movie_title, movie_overview, messages):
        # Get the last user message
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m["content"]
                break
        if not user_msg:
            return random.choice(GREETINGS)

        text = user_msg.strip()
        text_lower = text.lower()

        # Greetings
        if any(g in text_lower for g in ["hi", "hey", "hello", "sup", "yo", "what's up", "howdy"]) and len(text) < 30:
            return random.choice(GREETINGS)

        # Trivia request
        if any(t in text_lower for t in ["trivia", "fun fact", "did you know", "random fact", "surprise me", "tell me something"]):
            return random.choice(TRIVIA)

        # Director recommendations
        director = _detect_director(text)
        if director:
            return DIRECTOR_RECS[director]

        # Genre recommendations
        genre = _detect_genre(text)
        if genre:
            data = GENRE_RECOMMENDATIONS[genre]
            movies_list = _format_movie_list(data["movies"])
            return data["response"].format(movies=movies_list)

        # General recommendation request
        if any(w in text_lower for w in ["recommend", "suggest", "what should i watch", "what to watch", "movie suggestion", "best movie", "good movie", "top movie"]):
            genre = random.choice(list(GENRE_RECOMMENDATIONS.keys()))
            data = GENRE_RECOMMENDATIONS[genre]
            movies_list = _format_movie_list(data["movies"])
            intro = f"Let me pick a genre for you... how about **{genre}**?\n\n"
            return intro + data["response"].format(movies=movies_list)

        # Movie-specific context (when on a movie detail page)
        if movie_title:
            return (
                f"**{movie_title}** — great pick! "
                f"{'Here is what I know: ' + movie_overview[:200] + '...' if movie_overview else 'I love this one!'}\n\n"
                f"Want me to recommend similar movies? Just ask for the genre you're in the mood for!"
            )

        # Thank you / bye
        if any(w in text_lower for w in ["thanks", "thank you", "bye", "goodbye", "see ya", "later"]):
            return "Anytime! Happy watching — may your popcorn always be fresh and your screen always be big. See you at the movies!"

        # Fallback
        return random.choice(FALLBACK_RESPONSES)


chat_service = ChatService()
