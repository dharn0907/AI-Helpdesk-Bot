export const navItems = [
 ['Overview','LayoutDashboard'],['Companies','Building2'],['Chatbots','Bot'],['Conversations','MessagesSquare'],
 ['Tickets','Ticket'],['Customers','Users'],['Support Agents','Headset'],['Analytics & Reports','ChartNoAxesCombined'],
 ['AI Monitoring','BrainCircuit'],['System Logs','ScrollText'],['Admin Users & Roles','ShieldCheck'],['Settings','Settings']
]
export const companies = [
 {id:'ORG-001',name:'Northstar Retail',email:'ops@northstar.io',status:'Active',bots:4,conversations:12840,tickets:326,joined:'2026-02-14',last:'2 min ago'},
 {id:'ORG-002',name:'Vertex Healthcare',email:'admin@vertex.health',status:'Active',bots:2,conversations:8940,tickets:218,joined:'2026-03-02',last:'8 min ago'},
 {id:'ORG-003',name:'CloudNine SaaS',email:'team@cloudnine.app',status:'Active',bots:3,conversations:7240,tickets:142,joined:'2026-04-11',last:'18 min ago'},
 {id:'ORG-004',name:'UrbanCart',email:'hello@urbancart.in',status:'Inactive',bots:1,conversations:2180,tickets:94,joined:'2026-05-09',last:'3 days ago'},
 {id:'ORG-005',name:'Aster Learning',email:'support@aster.edu',status:'Suspended',bots:2,conversations:4860,tickets:181,joined:'2026-06-20',last:'12 days ago'}
]
export const chatbots = [
 {id:'BOT-1001',name:'Northstar Assistant',company:'Northstar Retail',status:'Active',deployment:'Deployed',conversations:8920,today:214,last:'1 min ago'},
 {id:'BOT-1002',name:'Returns Helper',company:'Northstar Retail',status:'Active',deployment:'Deployed',conversations:3920,today:83,last:'4 min ago'},
 {id:'BOT-2001',name:'Vertex Care Guide',company:'Vertex Healthcare',status:'Active',deployment:'Deployed',conversations:8940,today:172,last:'8 min ago'},
 {id:'BOT-3001',name:'CloudNine Support',company:'CloudNine SaaS',status:'Active',deployment:'Deployed',conversations:7240,today:146,last:'18 min ago'},
 {id:'BOT-4001',name:'UrbanCart Bot',company:'UrbanCart',status:'Inactive',deployment:'Paused',conversations:2180,today:0,last:'3 days ago'}
]
export const conversations = [
 {id:'CONV-89021',company:'Northstar Retail',bot:'Northstar Assistant',customer:'CUST-1042',started:'Today, 10:42 AM',last:'1 min ago',status:'Active',messages:12},
 {id:'CONV-89020',company:'Vertex Healthcare',bot:'Vertex Care Guide',customer:'CUST-2091',started:'Today, 10:37 AM',last:'6 min ago',status:'Resolved',messages:8},
 {id:'CONV-89019',company:'CloudNine SaaS',bot:'CloudNine Support',customer:'CUST-3028',started:'Today, 10:21 AM',last:'15 min ago',status:'Escalated',messages:17},
 {id:'CONV-89018',company:'Northstar Retail',bot:'Returns Helper',customer:'CUST-1188',started:'Today, 09:58 AM',last:'32 min ago',status:'Resolved',messages:6},
 {id:'CONV-89017',company:'Aster Learning',bot:'Aster Tutor',customer:'CUST-4071',started:'Today, 09:41 AM',last:'49 min ago',status:'Unresolved',messages:21}
]
export const tickets = [
 {id:'TKT-5812',company:'Northstar Retail',customer:'Aarav S.',subject:'Order not delivered',category:'Delivery',priority:'High',agent:'Maya R.',status:'Open',created:'Today, 10:31 AM'},
 {id:'TKT-5811',company:'Vertex Healthcare',customer:'Priya K.',subject:'Appointment confirmation',category:'Account',priority:'Medium',agent:'Rohan D.',status:'In Progress',created:'Today, 10:12 AM'},
 {id:'TKT-5810',company:'CloudNine SaaS',customer:'Sam T.',subject:'Unable to reset password',category:'Technical',priority:'Urgent',agent:'Unassigned',status:'Open',created:'Today, 09:54 AM'},
 {id:'TKT-5809',company:'Aster Learning',customer:'Nila P.',subject:'Course access issue',category:'Technical',priority:'Low',agent:'Ishan M.',status:'Resolved',created:'Yesterday'},
 {id:'TKT-5808',company:'UrbanCart',customer:'Dev R.',subject:'Refund request',category:'Refund',priority:'High',agent:'Maya R.',status:'Pending',created:'Yesterday'}
]
export const customers = [
 {id:'CUS-1042',name:'Aarav Sharma',email:'aarav@example.com',company:'Northstar Retail',conversations:18,tickets:2,last:'2 min ago'},
 {id:'CUS-2091',name:'Priya Kumar',email:'priya@example.com',company:'Vertex Healthcare',conversations:11,tickets:1,last:'6 min ago'},
 {id:'CUS-3028',name:'Sam Thomas',email:'sam@example.com',company:'CloudNine SaaS',conversations:7,tickets:3,last:'15 min ago'},
 {id:'CUS-1188',name:'Nila Prakash',email:'nila@example.com',company:'Northstar Retail',conversations:5,tickets:0,last:'32 min ago'}
]
export const agents = [
 {id:'AG-101',name:'Maya Raman',email:'maya@northstar.io',company:'Northstar Retail',status:'Online',assigned:14,resolved:182,pending:3,last:'Now'},
 {id:'AG-203',name:'Rohan Das',email:'rohan@vertex.health',company:'Vertex Healthcare',status:'Online',assigned:9,resolved:146,pending:2,last:'4 min ago'},
 {id:'AG-304',name:'Ishan Menon',email:'ishan@aster.edu',company:'Aster Learning',status:'Away',assigned:6,resolved:98,pending:4,last:'1 hour ago'}
]
export const errors = [
 {id:'ERR-9021',type:'LLM timeout',company:'CloudNine SaaS',bot:'CloudNine Support',severity:'High',time:'Today, 10:28 AM',status:'Investigating',detail:'Generation exceeded configured timeout (30s).'},
 {id:'ERR-9018',type:'Retrieval failure',company:'Aster Learning',bot:'Aster Tutor',severity:'Medium',time:'Today, 09:52 AM',status:'Open',detail:'No matching knowledge chunks returned.'},
 {id:'ERR-9011',type:'Empty response',company:'Northstar Retail',bot:'Returns Helper',severity:'Low',time:'Yesterday, 08:14 PM',status:'Resolved',detail:'Provider returned an empty completion.'}
]
export const logs = [
 {id:'LOG-7712',service:'API Gateway',level:'Info',message:'GET /health responded 200',time:'Today, 10:45 AM'},
 {id:'LOG-7711',service:'AI Runtime',level:'Error',message:'LLM request timed out for CloudNine',time:'Today, 10:28 AM'},
 {id:'LOG-7710',service:'Ticket Service',level:'Warning',message:'Ticket assignment is pending',time:'Today, 10:17 AM'},
 {id:'LOG-7709',service:'Database',level:'Info',message:'Connection pool healthy',time:'Today, 10:02 AM'}
]
export const activity = [
 ['Northstar Retail','New conversation started','2 min ago','MessageSquare'],
 ['Vertex Healthcare','Ticket #TKT-5811 updated','8 min ago','Ticket'],
 ['CloudNine SaaS','AI response latency spike detected','17 min ago','Activity'],
 ['UrbanCart','Company chatbot paused','3 days ago','PauseCircle']
]
export const trend = [
 {day:'Mon',conversations:840,tickets:34},{day:'Tue',conversations:970,tickets:42},{day:'Wed',conversations:910,tickets:39},
 {day:'Thu',conversations:1120,tickets:48},{day:'Fri',conversations:1280,tickets:51},{day:'Sat',conversations:1050,tickets:37},{day:'Sun',conversations:1390,tickets:56}
]
