/**
 * Service to handle loading and accessing local transcripts
 */

/**
 * Load all local transcripts from the public folder
 */
export const loadLocalTranscripts = async () => {
  try {
    // In a real implementation, we would fetch the list of transcript files
    // and load their contents. For now, we'll simulate success.
    
    // Simulated delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return {
      success: true,
      message: 'Local transcripts loaded successfully'
    };
  } catch (error) {
    console.error('Error loading local transcripts:', error);
    throw error;
  }
};

/**
 * Simulate searching through transcripts for relevant content
 */
export const searchTranscripts = async (query, mode) => {
  try {
    // In a real implementation, this would search through the actual transcript
    // content and return relevant passages. For now, we'll return simulated responses.
    
    // Simulated delay
    await new Promise(resolve => setTimeout(resolve, 300));
    
    let context;
    
    // Simulate different responses based on query keywords
    if (query.includes('solar') || query.includes('panel')) {
      context = "Solar panels have become increasingly efficient in recent years. Our top-tier panels operate at 22% efficiency and can generate up to 400W per panel in optimal conditions.";
    } else if (query.includes('price') || query.includes('cost')) {
      context = "Our solar panel installations typically range from $15,000 to $25,000 depending on the size of your home and energy needs. We offer financing options starting at 0% interest for qualified buyers.";
    } else if (query.includes('installation') || query.includes('install')) {
      context = "The installation process typically takes 1-3 days. Our team handles all permits and paperwork. We start with a site assessment, then design a custom system for your home.";
    } else {
      context = "Based on our sales calls, customers typically see a return on investment within 7-10 years. The solar panels come with a 25-year warranty and require minimal maintenance.";
    }
    
    return context;
  } catch (error) {
    console.error('Error searching transcripts:', error);
    throw error;
  }
};

export default {
  loadLocalTranscripts,
  searchTranscripts
};