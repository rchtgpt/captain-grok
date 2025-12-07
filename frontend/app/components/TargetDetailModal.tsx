'use client';

import { useState, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Target, TargetStatus } from '@/app/types';

interface TargetDetailModalProps {
  target: Target | null;
  onClose: () => void;
  onUpdate: (targetId: string, updates: { name?: string; description?: string }) => Promise<Target>;
  onDelete: (targetId: string) => Promise<void>;
  onAddPhotos: (targetId: string, photos: File[]) => Promise<Target>;
}

export function TargetDetailModal({ 
  target, 
  onClose, 
  onUpdate, 
  onDelete, 
  onAddPhotos 
}: TargetDetailModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isAddingPhotos, setIsAddingPhotos] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!target) return null;

  const getStatusBadge = (status: TargetStatus) => {
    switch (status) {
      case 'found':
        return <Badge className="bg-green-500 hover:bg-green-600">Found</Badge>;
      case 'confirmed':
        return <Badge className="bg-blue-500 hover:bg-blue-600">Confirmed</Badge>;
      default:
        return <Badge variant="outline" className="border-yellow-500 text-yellow-500">Searching</Badge>;
    }
  };

  const startEditing = () => {
    setEditName(target.name);
    setEditDescription(target.description);
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
    setEditName('');
    setEditDescription('');
  };

  const handleSave = async () => {
    if (!editName.trim()) return;
    
    setIsSaving(true);
    try {
      await onUpdate(target.id, {
        name: editName.trim(),
        description: editDescription.trim()
      });
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to update target:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(target.id);
      setShowDeleteConfirm(false);
      onClose();
    } catch (err) {
      console.error('Failed to delete target:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleAddPhotos = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    
    setIsAddingPhotos(true);
    try {
      await onAddPhotos(target.id, files);
    } catch (err) {
      console.error('Failed to add photos:', err);
    } finally {
      setIsAddingPhotos(false);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <>
      <Dialog open={!!target} onOpenChange={() => onClose()}>
        <DialogContent className="bg-zinc-900 border-zinc-800 text-white max-w-lg">
          <DialogHeader>
            <div className="flex items-center gap-3">
              {isEditing ? (
                <Input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="bg-zinc-800 border-zinc-700 text-lg font-semibold"
                  placeholder="Target name"
                />
              ) : (
                <DialogTitle className="text-xl">{target.name}</DialogTitle>
              )}
              {!isEditing && getStatusBadge(target.status)}
            </div>
          </DialogHeader>
          
          <div className="space-y-4 py-2">
            {/* Description */}
            <div>
              <Label className="text-xs text-zinc-400">Description</Label>
              {isEditing ? (
                <Textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="bg-zinc-800 border-zinc-700 mt-1 resize-none"
                  placeholder="Enter description..."
                  rows={2}
                />
              ) : (
                <p className="text-sm text-zinc-300 mt-1">
                  {target.description || 'No description'}
                </p>
              )}
            </div>
            
            {/* Status info */}
            {target.status === 'found' && (
              <div className="bg-green-900/30 border border-green-800 rounded-lg p-3">
                <p className="text-green-400 text-sm font-medium">Target Found!</p>
                <p className="text-green-300/80 text-xs mt-1">
                  Match confidence: {Math.round(target.matchConfidence * 100)}%
                </p>
                {target.foundAt && (
                  <p className="text-green-300/60 text-xs mt-1">
                    Found at: {new Date(target.foundAt).toLocaleString()}
                  </p>
                )}
              </div>
            )}
            
            {/* Reference Photos */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-xs text-zinc-400">
                  Reference Photos ({target.referencePhotos.length})
                </Label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleAddPhotos}
                  className="hidden"
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isAddingPhotos}
                  className="text-xs border-zinc-700 h-7"
                >
                  {isAddingPhotos ? 'Adding...' : '+ Add Photos'}
                </Button>
              </div>
              <ScrollArea className="w-full">
                <div className="flex gap-2 pb-2">
                  {target.referencePhotos.map((photo, index) => (
                    <div 
                      key={index}
                      className="w-20 h-20 rounded-md overflow-hidden flex-shrink-0 bg-zinc-800"
                    >
                      <img 
                        src={photo}
                        alt={`Reference ${index + 1}`}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
            
            {/* Matched Photos (if found) */}
            {target.matchedPhotos.length > 0 && (
              <div>
                <Label className="text-xs text-zinc-400 mb-2 block">
                  Matched Photos ({target.matchedPhotos.length})
                </Label>
                <ScrollArea className="w-full">
                  <div className="flex gap-2 pb-2">
                    {target.matchedPhotos.map((photo, index) => (
                      <div 
                        key={index}
                        className="w-20 h-20 rounded-md overflow-hidden flex-shrink-0 bg-zinc-800 ring-2 ring-green-500"
                      >
                        <img 
                          src={photo}
                          alt={`Match ${index + 1}`}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            )}
            
            {/* Created date */}
            <div className="text-xs text-zinc-500">
              Created: {new Date(target.createdAt).toLocaleString()}
            </div>
          </div>
          
          <DialogFooter className="flex-row justify-between sm:justify-between">
            <Button
              variant="destructive"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={isEditing || isDeleting}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </Button>
            
            <div className="flex gap-2">
              {isEditing ? (
                <>
                  <Button
                    variant="outline"
                    onClick={cancelEditing}
                    disabled={isSaving}
                    className="border-zinc-700"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSave}
                    disabled={isSaving || !editName.trim()}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {isSaving ? 'Saving...' : 'Save'}
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="outline"
                    onClick={startEditing}
                    className="border-zinc-700"
                  >
                    Edit
                  </Button>
                  <Button
                    onClick={onClose}
                    className="bg-zinc-700 hover:bg-zinc-600"
                  >
                    Close
                  </Button>
                </>
              )}
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent className="bg-zinc-900 border-zinc-800">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Delete Target?</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">
              Are you sure you want to delete &quot;{target.name}&quot;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              className="bg-zinc-800 border-zinc-700 text-white hover:bg-zinc-700"
              disabled={isDeleting}
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
