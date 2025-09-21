export const safeFetch = async (url: string, options?: RequestInit) => {
  try {
    console.log(`🔄 Calling API: ${url}`);
    
    const response = await fetch(url, options);
    
    // Check HTTP status
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    // Get raw text first
    const text = await response.text();
    console.log(`📝 Raw response: ${text}`);
    
    // Handle empty responses
    if (!text || text.trim().length === 0) {
      console.warn('⚠️ Empty response received');
      return null;
    }
    
    // Safely parse JSON
    try {
      const data = JSON.parse(text);
      console.log(`✅ Parsed JSON:`, data);
      return data;
    } catch (parseError) {
      console.error('❌ JSON parse error:', parseError);
      console.error('Response text was:', text);
      throw new Error(`Invalid JSON response: ${text.substring(0, 100)}...`);
    }
    
  } catch (error) {
    console.error('❌ API call failed:', error);
    throw error;
  }
};

// Test API connection
export const testConnection = async () => {
  try {
    const data = await safeFetch('/api/health');
    console.log('Backend connection test:', data);
    return data;
  } catch (error) {
    console.error('Backend connection failed:', error);
    throw error;
  }
};
