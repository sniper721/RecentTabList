#!/usr/bin/env python3
"""
Profanity Filter System for RTL
Blocks usernames, level names, and other content with inappropriate words
"""

import re
from typing import List, Tuple, Optional

class ProfanityFilter:
    """
    Profanity filter with customizable word lists and severity levels
    """
    
    def __init__(self):
        # Mild profanity - warnings but may be allowed in some contexts
        self.mild_words = [
            'damn', 'hell', 'crap', 'piss', 'ass', 'butt', 'fart', 'stupid', 'idiot', 'dumb'
        ]
        
        # Strong profanity - blocked in usernames and level names
        self.strong_words = [
            'fuck', 'shit', 'bitch', 'bastard', 'asshole', 'dickhead', 'prick', 'cock', 'dick', 'pussy',
            'whore', 'slut', 'cunt', 'twat', 'tits', 'boobs', 'penis', 'vagina', 'sex', 'porn',
            'masturbate', 'orgasm', 'horny', 'sexy', 'nude', 'naked', 'strip', 'rape', 'molest'
        ]
        
        # Hate speech and discriminatory language - always blocked
        self.hate_words = [
            'nigger', 'nigga', 'faggot', 'retard', 'retarded', 'gay', 'homo', 'lesbian', 'tranny',
            'nazi', 'hitler', 'jew', 'muslim', 'terrorist', 'kill', 'murder', 'suicide', 'die',
            'kys', 'kms', 'hang', 'shoot', 'bomb', 'explosion', 'attack', 'violence'
        ]
        
        # Leetspeak and common substitutions
        self.substitutions = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b',
            '@': 'a', '$': 's', '!': 'i', '+': 't', 'ph': 'f', 'ck': 'ck'
        }
        
        # Compile all words into one list with severity levels
        self.word_list = {
            **{word: 'mild' for word in self.mild_words},
            **{word: 'strong' for word in self.strong_words},
            **{word: 'hate' for word in self.hate_words}
        }
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text by removing special characters and applying substitutions
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove spaces, dots, dashes, underscores
        text = re.sub(r'[\s\.\-_]+', '', text)
        
        # Apply leetspeak substitutions
        for sub, replacement in self.substitutions.items():
            text = text.replace(sub, replacement)
        
        return text
    
    def check_word(self, word: str) -> Optional[Tuple[str, str]]:
        """
        Check if a single word contains profanity
        Returns (matched_word, severity) or None
        """
        normalized = self.normalize_text(word)
        
        for bad_word, severity in self.word_list.items():
            if bad_word in normalized:
                return (bad_word, severity)
        
        return None
    
    def check_text(self, text: str, strict: bool = True) -> Tuple[bool, List[Tuple[str, str]], str]:
        """
        Check text for profanity
        
        Args:
            text: Text to check
            strict: If True, blocks mild profanity too
            
        Returns:
            (is_clean, [(matched_word, severity), ...], reason)
        """
        if not text:
            return True, [], "Text is empty"
        
        violations = []
        normalized = self.normalize_text(text)
        
        # Check each word in our list
        for bad_word, severity in self.word_list.items():
            if bad_word in normalized:
                # Always block hate speech
                if severity == 'hate':
                    violations.append((bad_word, severity))
                # Block strong profanity
                elif severity == 'strong':
                    violations.append((bad_word, severity))
                # Block mild profanity only in strict mode
                elif severity == 'mild' and strict:
                    violations.append((bad_word, severity))
        
        if violations:
            severities = [v[1] for v in violations]
            if 'hate' in severities:
                reason = "Contains hate speech or discriminatory language"
            elif 'strong' in severities:
                reason = "Contains strong profanity"
            else:
                reason = "Contains inappropriate language"
            
            return False, violations, reason
        
        return True, [], "Text is clean"
    
    def check_username(self, username: str) -> Tuple[bool, str]:
        """
        Check username for profanity (strict mode)
        
        Returns:
            (is_allowed, reason)
        """
        is_clean, violations, reason = self.check_text(username, strict=True)
        
        if not is_clean:
            return False, f"Username not allowed: {reason}"
        
        return True, "Username is acceptable"
    
    def check_level_name(self, level_name: str) -> Tuple[bool, str]:
        """
        Check level name for profanity (strict mode)
        
        Returns:
            (is_allowed, reason)
        """
        is_clean, violations, reason = self.check_text(level_name, strict=True)
        
        if not is_clean:
            return False, f"Level name not allowed: {reason}"
        
        return True, "Level name is acceptable"
    
    def check_comment(self, comment: str) -> Tuple[bool, str]:
        """
        Check comment for profanity (less strict, allows mild words)
        
        Returns:
            (is_allowed, reason)
        """
        is_clean, violations, reason = self.check_text(comment, strict=False)
        
        if not is_clean:
            return False, f"Comment not allowed: {reason}"
        
        return True, "Comment is acceptable"
    
    def suggest_alternative(self, text: str) -> str:
        """
        Suggest a cleaned version of the text
        """
        normalized = self.normalize_text(text)
        cleaned = text
        
        for bad_word, severity in self.word_list.items():
            if bad_word in normalized:
                # Replace with asterisks
                replacement = '*' * len(bad_word)
                cleaned = re.sub(re.escape(bad_word), replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def add_word(self, word: str, severity: str = 'strong'):
        """
        Add a word to the filter list
        
        Args:
            word: Word to add
            severity: 'mild', 'strong', or 'hate'
        """
        if severity not in ['mild', 'strong', 'hate']:
            raise ValueError("Severity must be 'mild', 'strong', or 'hate'")
        
        self.word_list[word.lower()] = severity
        
        # Also add to the appropriate list
        if severity == 'mild' and word not in self.mild_words:
            self.mild_words.append(word.lower())
        elif severity == 'strong' and word not in self.strong_words:
            self.strong_words.append(word.lower())
        elif severity == 'hate' and word not in self.hate_words:
            self.hate_words.append(word.lower())
    
    def remove_word(self, word: str):
        """
        Remove a word from the filter list
        """
        word = word.lower()
        if word in self.word_list:
            severity = self.word_list[word]
            del self.word_list[word]
            
            # Remove from appropriate list
            if severity == 'mild' and word in self.mild_words:
                self.mild_words.remove(word)
            elif severity == 'strong' and word in self.strong_words:
                self.strong_words.remove(word)
            elif severity == 'hate' and word in self.hate_words:
                self.hate_words.remove(word)
    
    def get_word_lists(self) -> dict:
        """
        Get all word lists for admin management
        """
        return {
            'mild': sorted(self.mild_words),
            'strong': sorted(self.strong_words),
            'hate': sorted(self.hate_words)
        }

# Global instance
profanity_filter = ProfanityFilter()

def check_username_profanity(username: str) -> Tuple[bool, str]:
    """
    Convenience function to check username
    """
    return profanity_filter.check_username(username)

def check_level_name_profanity(level_name: str) -> Tuple[bool, str]:
    """
    Convenience function to check level name
    """
    return profanity_filter.check_level_name(level_name)

def check_comment_profanity(comment: str) -> Tuple[bool, str]:
    """
    Convenience function to check comment
    """
    return profanity_filter.check_comment(comment)

# Test function
if __name__ == "__main__":
    # Test the filter
    test_cases = [
        "normaluser",
        "badword123",
        "f*ck",
        "sh1t",
        "damn",
        "hello world",
        "test_user",
        "admin",
        "user@email.com"
    ]
    
    print("Testing Profanity Filter:")
    print("=" * 50)
    
    for test in test_cases:
        is_clean, reason = profanity_filter.check_username(test)
        status = "✅ ALLOWED" if is_clean else "❌ BLOCKED"
        print(f"{status}: '{test}' - {reason}")
    
    print("\nWord Lists:")
    print("=" * 50)
    lists = profanity_filter.get_word_lists()
    for severity, words in lists.items():
        print(f"{severity.upper()}: {len(words)} words")
        print(f"  {', '.join(words[:5])}{'...' if len(words) > 5 else ''}")