export interface GlossaryEntry {
  id: number;
  workId: number;
  volumeId?: number;
  sourceTerm: string;
  targetTerm: string;
  context?: string;
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface GlossaryCreate {
  sourceTerm: string;
  targetTerm: string;
  context?: string;
  notes?: string;
}

export interface GlossaryUpdate {
  targetTerm?: string;
  context?: string;
  notes?: string;
}
