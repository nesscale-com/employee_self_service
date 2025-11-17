# Mobile App API Usage Examples

This file contains example code snippets for integrating the Pollen Issue APIs into the ESS mobile app.

## JavaScript/React Native Examples

### 1. API Client Setup
```javascript
class IssueAPIClient {
    constructor(baseURL, authToken) {
        this.baseURL = baseURL;
        this.authToken = authToken;
    }

    async makeRequest(endpoint, method = 'GET', data = null) {
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.authToken}`,
                'X-Frappe-CSRF-Token': this.csrfToken
            }
        };

        if (data && (method === 'POST' || method === 'PUT')) {
            config.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(`${this.baseURL}/api/method/pollenkisan.mobile.v1.issue.${endpoint}`, config);
            const result = await response.json();
            
            if (result.http_status_code !== 200) {
                throw new Error(result.message);
            }
            
            return result.data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }
}
```

### 2. Initialize Options for Forms
```javascript
// Get all dropdown options for issue creation form
async function initializeIssueForm() {
    try {
        const options = await apiClient.makeRequest('get_issue_options');
        
        // Set dropdown data
        setIssueTypes(options.issue_types);
        setCustomers(options.customers);
        setPriorities(options.priorities);
        
        console.log('Form options loaded successfully');
    } catch (error) {
        console.error('Failed to load form options:', error);
    }
}
```

### 3. Create New Issue
```javascript
async function createIssue(issueData) {
    try {
        const newIssue = await apiClient.makeRequest('create', 'POST', {
            subject: issueData.subject,
            description: issueData.description,
            issue_type: issueData.issueType,
            customer: issueData.customer,
            priority: issueData.priority || 'Medium'
        });
        
        console.log('Issue created:', newIssue);
        return newIssue;
    } catch (error) {
        console.error('Failed to create issue:', error);
        throw error;
    }
}
```

### 4. Load Issues for Tabs
```javascript
// For Pending Issues Tab
async function loadPendingIssues(page = 0, pageSize = 20) {
    try {
        const result = await apiClient.makeRequest(
            `get_issue_list?list_type=pending&start=${page * pageSize}&page_length=${pageSize}`
        );
        
        return {
            issues: result.issues,
            totalCount: result.total_count,
            hasNext: result.has_next
        };
    } catch (error) {
        console.error('Failed to load pending issues:', error);
        return { issues: [], totalCount: 0, hasNext: false };
    }
}

// For All Issues Tab
async function loadAllIssues(page = 0, pageSize = 20, filters = {}) {
    try {
        const filterParam = Object.keys(filters).length > 0 ? 
            `&filters=${encodeURIComponent(JSON.stringify(filters))}` : '';
        
        const result = await apiClient.makeRequest(
            `get_issue_list?list_type=all&start=${page * pageSize}&page_length=${pageSize}${filterParam}`
        );
        
        return {
            issues: result.issues,
            totalCount: result.total_count,
            hasNext: result.has_next
        };
    } catch (error) {
        console.error('Failed to load all issues:', error);
        return { issues: [], totalCount: 0, hasNext: false };
    }
}
```

### 5. Issue Detail Screen
```javascript
async function loadIssueDetails(issueId) {
    try {
        const issue = await apiClient.makeRequest(`get_issue_details?name=${issueId}`);
        const history = await apiClient.makeRequest(`get_assignment_history?issue_id=${issueId}`);
        
        return {
            issue,
            assignmentHistory: history
        };
    } catch (error) {
        console.error('Failed to load issue details:', error);
        throw error;
    }
}
```

### 6. Issue Actions
```javascript
// Update Issue Status
async function updateIssueStatus(issueId, newStatus, comment = '') {
    try {
        const result = await apiClient.makeRequest('update_status', 'POST', {
            issue_id: issueId,
            status: newStatus,
            comment: comment
        });
        
        console.log('Status updated:', result);
        return result;
    } catch (error) {
        console.error('Failed to update status:', error);
        throw error;
    }
}

// Forward Issue
async function forwardIssue(issueId, toUser, comment = '') {
    try {
        const result = await apiClient.makeRequest('forward_issue', 'POST', {
            issue_id: issueId,
            to_user: toUser,
            comment: comment
        });
        
        console.log('Issue forwarded:', result);
        return result;
    } catch (error) {
        console.error('Failed to forward issue:', error);
        throw error;
    }
}

// Move Issue Backward
async function moveIssueBackward(issueId, comment = '') {
    try {
        const result = await apiClient.makeRequest('backward_issue', 'POST', {
            issue_id: issueId,
            comment: comment
        });
        
        console.log('Issue moved back:', result);
        return result;
    } catch (error) {
        console.error('Failed to move issue back:', error);
        throw error;
    }
}
```

### 7. Search Issues
```javascript
async function searchIssues(searchTerm, page = 0, pageSize = 20) {
    try {
        const result = await apiClient.makeRequest(
            `search_issues?search_term=${encodeURIComponent(searchTerm)}&start=${page * pageSize}&page_length=${pageSize}`
        );
        
        return {
            issues: result.issues,
            totalCount: result.total_count,
            hasNext: result.has_next,
            searchTerm: result.search_term
        };
    } catch (error) {
        console.error('Failed to search issues:', error);
        return { issues: [], totalCount: 0, hasNext: false, searchTerm };
    }
}
```

### 8. Dashboard Statistics
```javascript
async function loadDashboardStats() {
    try {
        const stats = await apiClient.makeRequest('get_issue_statistics');
        
        return {
            totalIssues: stats.total_issues,
            myPendingIssues: stats.my_pending_issues,
            myTotalIssues: stats.my_total_issues,
            highPriorityIssues: stats.my_high_priority,
            urgentIssues: stats.my_urgent_priority,
            closedIssues: stats.closed_issues,
            inProgressIssues: stats.in_progress_issues,
            pendingIssues: stats.pending_issues
        };
    } catch (error) {
        console.error('Failed to load dashboard stats:', error);
        return null;
    }
}
```

## React Native Component Examples

### 1. Issue List Component
```jsx
import React, { useState, useEffect } from 'react';
import { FlatList, Text, View, RefreshControl } from 'react-native';

const IssueListScreen = ({ listType = 'all' }) => {
    const [issues, setIssues] = useState([]);
    const [loading, setLoading] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [page, setPage] = useState(0);
    const [hasNext, setHasNext] = useState(true);

    const loadIssues = async (pageNum = 0, refresh = false) => {
        try {
            setLoading(true);
            
            const result = listType === 'pending' 
                ? await loadPendingIssues(pageNum)
                : await loadAllIssues(pageNum);
            
            if (refresh || pageNum === 0) {
                setIssues(result.issues);
            } else {
                setIssues(prev => [...prev, ...result.issues]);
            }
            
            setHasNext(result.hasNext);
            setPage(pageNum);
        } catch (error) {
            console.error('Error loading issues:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        loadIssues(0);
    }, [listType]);

    const handleRefresh = () => {
        setRefreshing(true);
        loadIssues(0, true);
    };

    const handleLoadMore = () => {
        if (hasNext && !loading) {
            loadIssues(page + 1);
        }
    };

    const renderIssueItem = ({ item }) => (
        <IssueListItem 
            issue={item} 
            onPress={() => navigation.navigate('IssueDetail', { issueId: item.name })}
        />
    );

    return (
        <FlatList
            data={issues}
            renderItem={renderIssueItem}
            keyExtractor={item => item.name}
            refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
            }
            onEndReached={handleLoadMore}
            onEndReachedThreshold={0.1}
            ListEmptyComponent={() => (
                <View style={styles.emptyContainer}>
                    <Text>No issues found</Text>
                </View>
            )}
        />
    );
};
```

### 2. Issue Creation Form
```jsx
const CreateIssueScreen = () => {
    const [formData, setFormData] = useState({
        subject: '',
        description: '',
        issueType: '',
        customer: '',
        priority: 'Medium'
    });
    const [options, setOptions] = useState({});
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        initializeIssueForm().then(setOptions);
    }, []);

    const handleSubmit = async () => {
        try {
            setLoading(true);
            const newIssue = await createIssue(formData);
            navigation.goBack();
            // Show success message
        } catch (error) {
            // Show error message
        } finally {
            setLoading(false);
        }
    };

    return (
        <ScrollView style={styles.container}>
            <TextInput
                placeholder="Issue Subject"
                value={formData.subject}
                onChangeText={text => setFormData({...formData, subject: text})}
            />
            
            <TextInput
                placeholder="Description"
                multiline
                value={formData.description}
                onChangeText={text => setFormData({...formData, description: text})}
            />
            
            <Picker
                selectedValue={formData.issueType}
                onValueChange={value => setFormData({...formData, issueType: value})}
            >
                {options.issue_types?.map(type => (
                    <Picker.Item key={type.name} label={type.issue_type} value={type.name} />
                ))}
            </Picker>
            
            <Button 
                title="Create Issue" 
                onPress={handleSubmit} 
                disabled={loading || !formData.subject || !formData.description}
            />
        </ScrollView>
    );
};
```

## Error Handling Best Practices

```javascript
// Centralized error handler
function handleAPIError(error, context = '') {
    console.error(`API Error in ${context}:`, error);
    
    // Show user-friendly message based on error
    if (error.message.includes('Not permitted')) {
        showAlert('Permission Error', 'You do not have permission to perform this action.');
    } else if (error.message.includes('required')) {
        showAlert('Validation Error', 'Please fill in all required fields.');
    } else {
        showAlert('Error', 'Something went wrong. Please try again.');
    }
}

// Usage in components
try {
    await createIssue(formData);
} catch (error) {
    handleAPIError(error, 'Create Issue');
}
```

## State Management (Redux/Context)

```javascript
// Actions
const issueActions = {
    loadPendingIssues: () => async dispatch => {
        dispatch({ type: 'ISSUES_LOADING' });
        try {
            const result = await loadPendingIssues();
            dispatch({ type: 'PENDING_ISSUES_LOADED', payload: result });
        } catch (error) {
            dispatch({ type: 'ISSUES_ERROR', payload: error.message });
        }
    },
    
    updateIssueStatus: (issueId, status, comment) => async dispatch => {
        try {
            const result = await updateIssueStatus(issueId, status, comment);
            dispatch({ type: 'ISSUE_STATUS_UPDATED', payload: { issueId, status } });
            return result;
        } catch (error) {
            dispatch({ type: 'ISSUES_ERROR', payload: error.message });
            throw error;
        }
    }
};
```