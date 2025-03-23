# modules/metadata_manager.py
import os
import json
import logging
import datetime
import shutil

logger = logging.getLogger(__name__)

class MetadataManager:
    """
    Handles reading, updating, and saving metadata for question images.
    """
    
    def __init__(self, metadata_file):
        """
        Initialize metadata manager with the path to the metadata file.
        
        Args:
            metadata_file (str): Path to the metadata JSON file
        """
        self.metadata_file = metadata_file
        self.backup_dir = os.path.join(os.path.dirname(metadata_file), 'metadata_backups')
        
        # Ensure backup directory exists
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def read_metadata(self):
        """
        Read the metadata file and parse the JSON.
        
        Returns:
            list: List of metadata entries, or empty list if file doesn't exist
        """
        if not os.path.exists(self.metadata_file):
            logger.warning(f"Metadata file not found: {self.metadata_file}")
            return []
        
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing metadata file: {str(e)}")
            return []
    
    def get_metadata_for_image(self, image_filename):
        """
        Find metadata entry for a specific image.
        
        Args:
            image_filename (str): Filename of the question image
            
        Returns:
            dict: Metadata entry for the image, or None if not found
        """
        metadata_list = self.read_metadata()
        
        for entry in metadata_list:
            if entry.get('filename') == image_filename:
                return entry
        
        return None
    
    def update_metadata(self, image_filename, enhanced_metadata):
        """
        Update metadata for a specific image with enhanced information.
        
        Args:
            image_filename (str): Filename of the question image
            enhanced_metadata (dict): Enhanced metadata to add/update
            
        Returns:
            bool: True if successful, False otherwise
        """
        # First create a backup
        self._create_backup()
        
        metadata_list = self.read_metadata()
        updated = False
        
        for entry in metadata_list:
            if entry.get('filename') == image_filename:
                # Update the entry with enhanced metadata
                for key, value in enhanced_metadata.items():
                    entry[key] = value
                
                # Add a timestamp for the update
                entry['last_updated'] = datetime.datetime.now().isoformat()
                updated = True
                break
        
        if not updated:
            # Create a new entry if none exists
            logger.info(f"Creating new metadata entry for {image_filename}")
            new_entry = {'filename': image_filename}
            
            # Update with enhanced metadata
            for key, value in enhanced_metadata.items():
                new_entry[key] = value
                
            # Add creation timestamp
            new_entry['created'] = datetime.datetime.now().isoformat()
            new_entry['last_updated'] = new_entry['created']
            
            # Add to metadata list
            metadata_list.append(new_entry)
            updated = True
        
        # Save the updated metadata
        return self._save_metadata(metadata_list)
    
    def update_batch_metadata(self, updates):
        """
        Update metadata for multiple images.
        
        Args:
            updates (list): List of tuples (image_filename, enhanced_metadata)
            
        Returns:
            tuple: (success_count, failure_count)
        """
        if not updates:
            return (0, 0)
        
        # First create a backup
        self._create_backup()
        
        metadata_list = self.read_metadata()
        success_count = 0
        failure_count = 0
        
        for image_filename, enhanced_metadata in updates:
            updated = False
            
            for entry in metadata_list:
                if entry.get('filename') == image_filename:
                    # Update the entry with enhanced metadata
                    for key, value in enhanced_metadata.items():
                        entry[key] = value
                    
                    # Add a timestamp for the update
                    entry['last_updated'] = datetime.datetime.now().isoformat()
                    updated = True
                    success_count += 1
                    break
            
            if not updated:
                logger.warning(f"No metadata entry found for {image_filename}")
                failure_count += 1
        
        # Save the updated metadata
        if self._save_metadata(metadata_list):
            return (success_count, failure_count)
        else:
            # If save failed, count all as failures
            return (0, success_count + failure_count)
    
    def _create_backup(self):
        """
        Create a backup of the metadata file before making changes.
        
        Returns:
            bool: True if backup was created, False otherwise
        """
        if not os.path.exists(self.metadata_file):
            logger.warning(f"Cannot create backup: file {self.metadata_file} not found")
            return False
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"metadata_backup_{timestamp}.json"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            shutil.copy2(self.metadata_file, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            return False
    
    def _save_metadata(self, metadata_list):
        """
        Save the metadata list to the metadata file.
        
        Args:
            metadata_list (list): List of metadata entries
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata_list, f, indent=4)
            
            logger.info(f"Metadata saved to {self.metadata_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata: {str(e)}")
            return False
        
        