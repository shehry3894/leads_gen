from datetime import datetime


def get_demo_leads():
    """
    Return a small set of demo lead rows that mimic the real scraper output.
    Used when TESTING mode is enabled to validate end-to-end flow without
    hitting Google Maps or external websites.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return [
        {
            "Name": "Demo Gym One",
            "Google Maps Link": "https://maps.google.com/?cid=123",
            "Address": "123 Demo Street, New York, NY",
            "Phone": "+1 555-0100",
            "WhatsApp": "https://wa.me/15550100",
            "Website": "https://demogymone.example.com",
            "Rating": "4.7",
            "Review Count": "245",
            "Facebook": "https://facebook.com/demogymone",
            "Instagram": "https://instagram.com/demogymone",
            "Twitter": "https://twitter.com/demogymone",
            "LinkedIn": "https://linkedin.com/company/demogymone",
            "YouTube": None,
            "Pinterest": None,
            "TikTok": None,
            "Threads": None,
            "Snapchat": None,
            "Emails": "info@demogymone.example.com",
            "Scraped Time": now,
        },
        {
            "Name": "Demo Fitness Club",
            "Google Maps Link": "https://maps.google.com/?cid=456",
            "Address": "456 Sample Ave, New York, NY",
            "Phone": "+1 555-0200",
            "WhatsApp": "https://wa.me/15550200",
            "Website": "https://demofitness.example.com",
            "Rating": "4.3",
            "Review Count": "87",
            "Facebook": None,
            "Instagram": "https://instagram.com/demofitness",
            "Twitter": None,
            "LinkedIn": None,
            "YouTube": None,
            "Pinterest": None,
            "TikTok": None,
            "Threads": None,
            "Snapchat": None,
            "Emails": "contact@demofitness.example.com",
            "Scraped Time": now,
        },
        {
            "Name": "Demo Yoga Studio",
            "Google Maps Link": "https://maps.google.com/?cid=789",
            "Address": "789 Example Blvd, New York, NY",
            "Phone": "N/A",
            "WhatsApp": "N/A",
            "Website": "https://demoyoga.example.com",
            "Rating": "4.9",
            "Review Count": "512",
            "Facebook": "https://facebook.com/demoyoga",
            "Instagram": "https://instagram.com/demoyoga",
            "Twitter": None,
            "LinkedIn": None,
            "YouTube": None,
            "Pinterest": None,
            "TikTok": None,
            "Threads": None,
            "Snapchat": None,
            "Emails": "hello@demoyoga.example.com",
            "Scraped Time": now,
        },
    ]
