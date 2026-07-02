import { NextRequest, NextResponse } from 'next/server';
import { DEMO_PATIENTS } from '@/lib/mock-data';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const patient = DEMO_PATIENTS.find(p => p.id === id);
    
    if (!patient) {
      return NextResponse.json({ error: 'Patient not found' }, { status: 404 });
    }
    
    // Return mock data with a previewMode indicator
    return NextResponse.json({ ...patient, previewMode: true });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Internal server error';
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
