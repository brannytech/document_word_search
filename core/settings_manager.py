"""Settings management with presets and persistence"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class PerformanceSettings:
    """Performance-related settings"""
    max_workers: int = 8
    batch_size: int = 100
    min_files_for_batching: int = 50
    search_mode: str = "hybrid"  # hybrid, fast_extract, indexed_only


@dataclass
class ContextSettings:
    """Context display settings"""
    sentences_before: int = 2
    sentences_after: int = 2
    max_merge_distance: int = 5


@dataclass
class CacheSettings:
    """Cache configuration"""
    enabled: bool = True
    max_size_mb: int = 500
    persistent: bool = False
    auto_preextract_threshold: int = 100


@dataclass
class IndexSettings:
    """Index configuration"""
    enabled: bool = True
    auto_index: bool = True
    index_path: str = "document_index.db"
    rebuild_on_startup: bool = False


@dataclass
class UserSettings:
    """Complete user settings"""
    performance: PerformanceSettings
    context: ContextSettings
    cache: CacheSettings
    index: IndexSettings
    profile: str = "balanced"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'performance': asdict(self.performance),
            'context': asdict(self.context),
            'cache': asdict(self.cache),
            'index': asdict(self.index),
            'profile': self.profile
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSettings':
        """Create from dictionary"""
        # Handle legacy settings without search_mode
        perf_data = data.get('performance', {})
        if 'search_mode' not in perf_data:
            perf_data['search_mode'] = 'hybrid'
        
        # Handle legacy settings without index
        index_data = data.get('index', {})
        if not index_data:
            index_data = {
                'enabled': True,
                'auto_index': True,
                'index_path': 'document_index.db',
                'rebuild_on_startup': False
            }
        
        return cls(
            performance=PerformanceSettings(**perf_data),
            context=ContextSettings(**data.get('context', {})),
            cache=CacheSettings(**data.get('cache', {})),
            index=IndexSettings(**index_data),
            profile=data.get('profile', 'balanced')
        )


class SettingsManager:
    """Manage user settings with presets and persistence"""
    
    SETTINGS_FILE = Path("user_settings.json")
    
    PRESETS = {
        'low_resource': UserSettings(
            performance=PerformanceSettings(
                max_workers=2, 
                batch_size=50, 
                min_files_for_batching=50,
                search_mode="fast_extract"
            ),
            context=ContextSettings(
                sentences_before=2, 
                sentences_after=2, 
                max_merge_distance=5
            ),
            cache=CacheSettings(
                enabled=False, 
                max_size_mb=100, 
                persistent=False, 
                auto_preextract_threshold=100
            ),
            index=IndexSettings(
                enabled=False,
                auto_index=False,
                index_path='document_index.db',
                rebuild_on_startup=False
            ),
            profile='low_resource'
        ),
        'balanced': UserSettings(
            performance=PerformanceSettings(
                max_workers=8, 
                batch_size=100, 
                min_files_for_batching=50,
                search_mode="hybrid"
            ),
            context=ContextSettings(
                sentences_before=2, 
                sentences_after=2, 
                max_merge_distance=5
            ),
            cache=CacheSettings(
                enabled=True, 
                max_size_mb=500, 
                persistent=False, 
                auto_preextract_threshold=100
            ),
            index=IndexSettings(
                enabled=True,
                auto_index=True,
                index_path='document_index.db',
                rebuild_on_startup=False
            ),
            profile='balanced'
        ),
        'high_performance': UserSettings(
            performance=PerformanceSettings(
                max_workers=16, 
                batch_size=200, 
                min_files_for_batching=50,
                search_mode="hybrid"
            ),
            context=ContextSettings(
                sentences_before=2, 
                sentences_after=2, 
                max_merge_distance=5
            ),
            cache=CacheSettings(
                enabled=True, 
                max_size_mb=1000, 
                persistent=False, 
                auto_preextract_threshold=100
            ),
            index=IndexSettings(
                enabled=True,
                auto_index=True,
                index_path='document_index.db',
                rebuild_on_startup=False
            ),
            profile='high_performance'
        ),
        'maximum': UserSettings(
            performance=PerformanceSettings(
                max_workers=32, 
                batch_size=500, 
                min_files_for_batching=30,
                search_mode="indexed_only"
            ),
            context=ContextSettings(
                sentences_before=3, 
                sentences_after=3, 
                max_merge_distance=5
            ),
            cache=CacheSettings(
                enabled=True, 
                max_size_mb=2000, 
                persistent=True, 
                auto_preextract_threshold=50
            ),
            index=IndexSettings(
                enabled=True,
                auto_index=True,
                index_path='document_index.db',
                rebuild_on_startup=False
            ),
            profile='maximum'
        )
    }
    
    @classmethod
    def load_settings(cls) -> UserSettings:
        """Load settings from file or return defaults"""
        if cls.SETTINGS_FILE.exists():
            try:
                with open(cls.SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                return UserSettings.from_dict(data)
            except Exception as e:
                print(f"Error loading settings: {e}")
                return cls.get_preset('balanced')
        return cls.get_preset('balanced')
    
    @classmethod
    def save_settings(cls, settings: UserSettings):
        """Save settings to file"""
        try:
            with open(cls.SETTINGS_FILE, 'w') as f:
                json.dump(settings.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    @classmethod
    def get_preset(cls, preset_name: str) -> UserSettings:
        """Get a preset configuration"""
        return cls.PRESETS.get(preset_name, cls.PRESETS['balanced'])
    
    @classmethod
    def get_preset_names(cls):
        """Get list of preset names"""
        return list(cls.PRESETS.keys())