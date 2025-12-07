'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import type { Target } from '@/app/types';
import type { TargetsState } from '@/app/hooks/useTargets';
import { AddTargetModal } from './AddTargetModal';
import { TargetDetailModal } from './TargetDetailModal';

interface TargetsPanelProps {
  targetsState: TargetsState;
  onTail?: (targetId: string) => void;
  tailingTargetId?: string | null;
}

export function TargetsPanel({ targetsState, onTail, tailingTargetId }: TargetsPanelProps) {
  const { 
    targets, 
    stats, 
    isLoading, 
    error, 
    selectedTarget,
    selectTarget,
    createTarget,
    updateTarget,
    deleteTarget,
    addPhotos
  } = targetsState;
  
  const [showAddModal, setShowAddModal] = useState(false);

  const getStatusBadge = (status: Target['status']) => {
    switch (status) {
      case 'found':
        return <Badge className="bg-green-500 hover:bg-green-600">Found</Badge>;
      case 'confirmed':
        return <Badge className="bg-blue-500 hover:bg-blue-600">Confirmed</Badge>;
      default:
        return <Badge variant="outline" className="border-yellow-500 text-yellow-500">Searching</Badge>;
    }
  };

  if (error) {
    return (
      <Card className="h-full bg-zinc-900 border-zinc-800">
        <CardContent className="flex items-center justify-center h-full">
          <p className="text-red-400 text-sm">{error}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full bg-zinc-900 border-zinc-800 flex flex-col">
      <CardHeader className="pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-white">
            Search Targets
          </CardTitle>
          <Button 
            size="sm" 
            onClick={() => setShowAddModal(true)}
            className="bg-blue-600 hover:bg-blue-700"
          >
            + Add Target
          </Button>
        </div>
        {stats && (
          <div className="flex gap-4 text-xs text-zinc-400 mt-2">
            <span>{stats.total} total</span>
            <span className="text-green-400">{stats.found} found</span>
            <span className="text-yellow-400">{stats.searching} searching</span>
          </div>
        )}
      </CardHeader>
      
      <CardContent className="flex-1 overflow-hidden pt-0">
        <ScrollArea className="h-full pr-4">
          {isLoading && targets.length === 0 ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center gap-3 p-3 bg-zinc-800 rounded-lg">
                  <Skeleton className="w-12 h-12 rounded-md" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
              ))}
            </div>
          ) : targets.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-center">
              <p className="text-zinc-400 text-sm mb-2">No targets yet</p>
              <p className="text-zinc-500 text-xs">
                Add a target to search for using facial recognition
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {targets.map(target => (
                <button
                  key={target.id}
                  onClick={() => selectTarget(target)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors text-left ${
                    selectedTarget?.id === target.id 
                      ? 'bg-zinc-700 ring-1 ring-blue-500' 
                      : 'bg-zinc-800 hover:bg-zinc-750'
                  }`}
                >
                  {/* Reference photo thumbnail */}
                  <div className="w-12 h-12 rounded-md overflow-hidden bg-zinc-700 flex-shrink-0">
                    {target.referencePhotos.length > 0 ? (
                      <img 
                        src={target.referencePhotos[0]} 
                        alt={target.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-zinc-500">
                        ?
                      </div>
                    )}
                  </div>
                  
                  {/* Target info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white truncate">
                        {target.name}
                      </span>
                      {getStatusBadge(target.status)}
                    </div>
                    <p className="text-xs text-zinc-400 truncate mt-0.5">
                      {target.description || 'No description'}
                    </p>
                    {target.status === 'found' && target.matchConfidence > 0 && (
                      <p className="text-xs text-green-400 mt-0.5">
                        {Math.round(target.matchConfidence * 100)}% match confidence
                      </p>
                    )}
                  </div>
                  
                  {/* Tail button for found targets */}
                  {target.status === 'found' && onTail && (
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        onTail(target.id);
                      }}
                      disabled={tailingTargetId === target.id}
                      className={`flex-shrink-0 text-xs h-7 ${
                        tailingTargetId === target.id 
                          ? 'bg-green-600 hover:bg-green-600 cursor-default' 
                          : 'bg-emerald-600 hover:bg-emerald-700'
                      }`}
                    >
                      {tailingTargetId === target.id ? 'Tailing...' : 'Tail'}
                    </Button>
                  )}
                  
                  {/* Photo count - only show if not tailing */}
                  {!(target.status === 'found' && onTail) && (
                    <div className="text-xs text-zinc-500 flex-shrink-0">
                      {target.referencePhotos.length} photo{target.referencePhotos.length !== 1 ? 's' : ''}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
      
      {/* Add Target Modal */}
      <AddTargetModal
        open={showAddModal}
        onOpenChange={setShowAddModal}
        onSubmit={createTarget}
      />
      
      {/* Target Detail Modal */}
      <TargetDetailModal
        target={selectedTarget}
        onClose={() => selectTarget(null)}
        onUpdate={updateTarget}
        onDelete={deleteTarget}
        onAddPhotos={addPhotos}
      />
    </Card>
  );
}
