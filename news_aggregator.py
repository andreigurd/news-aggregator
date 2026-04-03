import hashlib
import requests
import os
import json
from datetime import datetime, timedelta
from tabulate import tabulate
from collections import Counter

class NewsAggregator:
    def __init__(self):
        self.api_key = os.getenv('NEWS_API_KEY')
        if not self.api_key:
            raise ValueError("NEWS_API_KEY environment variable not set")

        self.base_url = "https://newsapi.org/v2"
        self.favorites = self.load_favorites()

    def get_top_headlines(self, country='us', category=None):
        """Get top headlines"""
        url = f"{self.base_url}/top-headlines"
        params = {
            'country': country,
            'apiKey': self.api_key
        }

        if category:
            params['category'] = category

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching headlines: {e}")
            return None

    def search_news(self, query, from_date=None, to_date=None, sort_by='publishedAt'):
        """Search for news articles"""
        url = f"{self.base_url}/everything"
        params = {
            'q': query,
            'apiKey': self.api_key,
            'sortBy': sort_by,
            'language': 'en'
        }

        if from_date:
            params['from'] = from_date

        if to_date:
            params['to'] = to_date

        if sort_by:
            params['sortBy'] = sort_by

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error searching news: {e}")
            return None

    def display_articles(self, data):
        """Display articles in a nice format"""
        if not data or 'articles' not in data:
            print("No articles to display")
            return

        articles = data['articles']

        print(f"\nFound {len(articles)} articles\n")

        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            print(f"   Source: {article['source']['name']}")
            print(f"   Published: {article['publishedAt'][:10]}")
            if article.get('description'):
                desc = article['description'][:100]
                print(f"   {desc}...")
            print(f"   URL: {article['url']}\n")

    def save_favorite(self, article, category='Unknown'):
        """Save article to favorites"""
        favorite = {
            'title': article['title'],
            'source': article['source']['name'],
            'category': category,
            'url': article['url'],
            'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        self.favorites.append(favorite)
        self._save_favorites()
        print(f"Saved to favorites: {article['title'][:50]}...")

    def show_favorites(self):
        """Display saved favorites"""
        if not self.favorites:
            print("No favorites saved yet!")
            return

        print(f"\nYour Favorites ({len(self.favorites)} articles)\n")

        table_data = []
        for i, fav in enumerate(self.favorites, 1):
            table_data.append([
                i,
                fav['title'][:50] + "..." if len(fav['title']) > 50 else fav['title'],
                fav['source'],
                fav['saved_at'][:10]
            ])

        headers = ["#", "Title", "Source", "Saved"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        return table_data

    def delete_favorite(self):
        """Delete a favorite by index number"""

        if not self.favorites:
            print("No favorites saved yet!")
            return
        
        table_data = self.show_favorites()
        tot_fav_index = len(table_data)

        while True:
                try:
                    delete_choice = int(input("Select article number to delete: "))
                    if 1 <= delete_choice and delete_choice <= tot_fav_index:
                        print(f"Article number {delete_choice} deleted.")             
                        removed_fav = self.favorites.pop(delete_choice-1) 
                        print(f"Deleted: {removed_fav['title'][:50]}")
                        self._save_favorites()
                        return 
                    else:
                        print("Number out of range. Please try again.")                        

                except ValueError:
                    print("Invalid entry. Please try again.")

    def summary_statistics(self):
        if not self.favorites:
            print("No favorites saved yet!")
            return
        
        print("Statistics Summary")
        print("=" * 60)

        # most common source
        sources_list =[]
        for source_item in self.favorites:
            if source_item['source']:
                sources_list.append(source_item['source'])
        most_common_source, count = Counter(sources_list).most_common(1)[0]
        print(f'\nMost Common Source: {most_common_source}: {count} articles')

        # category breakdown (quantity of each category)
        categories_list =[]
        for cat_item in self.favorites:
            if cat_item['category']:
                categories_list.append(cat_item['category'])
        category_counts = Counter(categories_list)
        print(f'\nCategory Breakdown')
        print("=" * 20)
        for cat_item, count in category_counts.items():
            print(f'{cat_item}: {count} articles(s)')

        

    def load_favorites(self):
        """Load favorites from file"""
        try:
            with open('favorites.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _save_favorites(self):
        """Save favorites to file"""
        with open('favorites.json', 'w') as f:
            json.dump(self.favorites, f, indent=2)

    def export_favorites(self):
        """Export favorites to text file"""
        if not self.favorites:
            print("No favorites saved yet!")
            return
        
        now = datetime.now()
        date_string = now.strftime("%Y-%m-%d %H:%M:%S")
        date_now = date_string[:10]

        table_data = self.show_favorites()
        headers = ["#", "Title", "Source", "Saved"]

        with open(f"{date_now} favorite_articles.txt", "w", newline="", encoding="utf-8-sig") as file:
            file.write(tabulate(table_data, headers=headers, tablefmt="grid"))

        file_path = os.path.abspath(f"{date_now} favorite_articles.txt")
        print(f"Text file exported to:\n{file_path}")

class CachedNewsAggregator(NewsAggregator):
    # class (xx) becomes child of xx
    def __init__(self):
            super().__init__()
            self.cache = {}
            self.cache_duration = timedelta(minutes=30)

    def _cache_key(self, endpoint, params):
        """Generate cache key from request"""
        key_string = f"{endpoint}:{str(sorted(params.items()))}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cached(self, cache_key):
        """Get from cache if fresh"""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_duration:
                print("(Using cached data)")
                return data
        return None

    def get_top_headlines(self, country='us', category=None):
        """Get top headlines"""
        url = f"{self.base_url}/top-headlines"
        params = {
            'country': country,
            'apiKey': self.api_key
        }

        if category:
            params['category'] = category

        # make cache key
        cache_key = self._cache_key("headlines", params)

        #Check if we have recent cached data. note _get_cached also checks that cache is fresh
        cached_data = self._get_cached(cache_key)
        if cached_data:
            return cached_data

        # if cache_key in self.cache:
        #     cached_data, timestamp = self._get_cached(cache_key)
        
        # No cache or cache expired - fetch new data
        # call parent class to avoid repeating (DRY)
        data = super().get_top_headlines(country=country, category=category)

        # Save to cache
        if data:
            self.cache[cache_key] = (data, datetime.now())
            # note this is .cache data to cache_key location

        return data

def main():
    """Main program"""
    aggregator = CachedNewsAggregator()

    print("News Aggregator")
    print("=" * 60)

    while True:
        print("\nOptions:")
        print("1. Top headlines")
        print("2. Headlines by category")
        print("3. Search news")
        print("4. View favorites")
        print("5. Filter by date range")
        print("6. Sorted search by date")
        print("7. Sorted search by relevance")
        print("8. Delete from favorites")
        print("9. Export favorites")
        print("10. Show favorites summary statistics ")
        print("0. Quit")

        choice = input("\nChoose an option: ")

        if choice == "1":
            data = aggregator.get_top_headlines()
            aggregator.display_articles(data)

            if data and data['articles']:
                save = input("\nSave any article? (enter number or 'n'): ")
                if save.lower() != 'n':
                    try:
                        idx = int(save) - 1
                        aggregator.save_favorite(data['articles'][idx])
                    except (ValueError, IndexError):
                        print("Invalid selection")

        elif choice == "2":
            print("\nCategories: business, entertainment, general, health, science, sports, technology")
            category = input("Choose category: ")
            data = aggregator.get_top_headlines(category=category)
            aggregator.display_articles(data)

            if data and data['articles']:
                save = input("\nSave any article? (enter number or 'n'): ")
                if save.lower() != 'n':
                    try:
                        idx = int(save) - 1
                        aggregator.save_favorite(data['articles'][idx], category)
                    except (ValueError, IndexError):
                        print("Invalid selection")

        elif choice == "3":
            query = input("Search for: ")
            data = aggregator.search_news(query)
            aggregator.display_articles(data)

            if data and data['articles']:
                save = input("\nSave any article? (enter number or 'n'): ")
                if save.lower() != 'n':
                    try:
                        idx = int(save) - 1
                        # not searching by category so save category as "unkown" in save_favorite(self, article, category='Unknown')
                        aggregator.save_favorite(data['articles'][idx])
                    except (ValueError, IndexError):
                        print("Invalid selection")

        elif choice == "4":
            aggregator.show_favorites()

        elif choice == "5":
            
            from_date = input("Enter beginning date (YYYY-MM-DD): ")
            to_date = input("Enter end date (YYYY-MM-DD): ")
            data = aggregator.search_news(from_date, to_date)
            aggregator.display_articles(data)
            
        elif choice == "6":
            # sortBy has options: relevancy, popularity, and publishedAt
            query = input("Search for: ")
            data = aggregator.search_news(query, sort_by='publishedAt')
            aggregator.display_articles(data)
        #Sort articles by date
        elif choice == "7":
            query = input("Search for: ")
            data = aggregator.search_news(query, sort_by='relevancy')
            aggregator.display_articles(data)
        #Sort articles by relevance

        elif choice == "8":
            aggregator.delete_favorite()
        #Delete from favorites

        elif choice == "9":
            aggregator.export_favorites()
            #Export favorites

        elif choice == "10":
            aggregator.summary_statistics()
        #Show summary statistics
        
        elif choice == "0":
            print("Goodbye!")
            break

        else:
            print("Invalid choice!")

if __name__ == "__main__":
    main()
