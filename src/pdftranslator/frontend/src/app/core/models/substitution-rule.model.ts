export interface SubstitutionRule {
  id: number;
  name: string;
  pattern: string;
  replacement: string;
  description?: string;
  is_active: boolean;
  apply_on_extract: boolean;
  created_at: string;
  updated_at?: string;
}

export interface SubstitutionRuleCreate {
  name: string;
  pattern: string;
  replacement: string;
  description?: string;
  is_active?: boolean;
  apply_on_extract?: boolean;
}

export interface SubstitutionRuleUpdate {
  name?: string;
  pattern?: string;
  replacement?: string;
  description?: string;
  is_active?: boolean;
  apply_on_extract?: boolean;
}

export interface ApplyRulesRequest {
  rule_ids?: number[];
}
