// Comprehensive country list with search functionality for RTL
const COUNTRIES = [
    { code: 'AD', name: 'Andorra', flag: '🇦🇩' },
    { code: 'AE', name: 'United Arab Emirates', flag: '🇦🇪' },
    { code: 'AF', name: 'Afghanistan', flag: '🇦🇫' },
    { code: 'AG', name: 'Antigua and Barbuda', flag: '🇦🇬' },
    { code: 'AL', name: 'Albania', flag: '🇦🇱' },
    { code: 'AM', name: 'Armenia', flag: '🇦🇲' },
    { code: 'AO', name: 'Angola', flag: '🇦🇴' },
    { code: 'AR', name: 'Argentina', flag: '🇦🇷' },
    { code: 'AT', name: 'Austria', flag: '🇦🇹' },
    { code: 'AU', name: 'Australia', flag: '🇦🇺' },
    { code: 'AZ', name: 'Azerbaijan', flag: '🇦🇿' },
    { code: 'BA', name: 'Bosnia and Herzegovina', flag: '🇧🇦' },
    { code: 'BB', name: 'Barbados', flag: '🇧🇧' },
    { code: 'BD', name: 'Bangladesh', flag: '🇧🇩' },
    { code: 'BE', name: 'Belgium', flag: '🇧🇪' },
    { code: 'BF', name: 'Burkina Faso', flag: '🇧🇫' },
    { code: 'BG', name: 'Bulgaria', flag: '🇧🇬' },
    { code: 'BH', name: 'Bahrain', flag: '🇧🇭' },
    { code: 'BI', name: 'Burundi', flag: '🇧🇮' },
    { code: 'BJ', name: 'Benin', flag: '🇧🇯' },
    { code: 'BN', name: 'Brunei', flag: '🇧🇳' },
    { code: 'BO', name: 'Bolivia', flag: '🇧🇴' },
    { code: 'BR', name: 'Brazil', flag: '🇧🇷' },
    { code: 'BS', name: 'Bahamas', flag: '🇧🇸' },
    { code: 'BT', name: 'Bhutan', flag: '🇧🇹' },
    { code: 'BW', name: 'Botswana', flag: '🇧🇼' },
    { code: 'BY', name: 'Belarus', flag: '🇧🇾' },
    { code: 'BZ', name: 'Belize', flag: '🇧🇿' },
    { code: 'CA', name: 'Canada', flag: '🇨🇦' },
    { code: 'CD', name: 'Congo (DRC)', flag: '🇨🇩' },
    { code: 'CF', name: 'Central African Republic', flag: '🇨🇫' },
    { code: 'CG', name: 'Congo', flag: '🇨🇬' },
    { code: 'CH', name: 'Switzerland', flag: '🇨🇭' },
    { code: 'CI', name: 'Côte d\'Ivoire', flag: '🇨🇮' },
    { code: 'CL', name: 'Chile', flag: '🇨🇱' },
    { code: 'CM', name: 'Cameroon', flag: '🇨🇲' },
    { code: 'CN', name: 'China', flag: '🇨🇳' },
    { code: 'CO', name: 'Colombia', flag: '🇨🇴' },
    { code: 'CR', name: 'Costa Rica', flag: '🇨🇷' },
    { code: 'CU', name: 'Cuba', flag: '🇨🇺' },
    { code: 'CV', name: 'Cape Verde', flag: '🇨🇻' },
    { code: 'CY', name: 'Cyprus', flag: '🇨🇾' },
    { code: 'CZ', name: 'Czech Republic', flag: '🇨🇿' },
    { code: 'DE', name: 'Germany', flag: '🇩🇪' },
    { code: 'DJ', name: 'Djibouti', flag: '🇩🇯' },
    { code: 'DK', name: 'Denmark', flag: '🇩🇰' },
    { code: 'DM', name: 'Dominica', flag: '🇩🇲' },
    { code: 'DO', name: 'Dominican Republic', flag: '🇩🇴' },
    { code: 'DZ', name: 'Algeria', flag: '🇩🇿' },
    { code: 'EC', name: 'Ecuador', flag: '🇪🇨' },
    { code: 'EE', name: 'Estonia', flag: '🇪🇪' },
    { code: 'EG', name: 'Egypt', flag: '🇪🇬' },
    { code: 'ER', name: 'Eritrea', flag: '🇪🇷' },
    { code: 'ES', name: 'Spain', flag: '🇪🇸' },
    { code: 'ET', name: 'Ethiopia', flag: '🇪🇹' },
    { code: 'FI', name: 'Finland', flag: '🇫🇮' },
    { code: 'FJ', name: 'Fiji', flag: '🇫🇯' },
    { code: 'FR', name: 'France', flag: '🇫🇷' },
    { code: 'GA', name: 'Gabon', flag: '🇬🇦' },
    { code: 'GB', name: 'United Kingdom', flag: '🇬🇧' },
    { code: 'GD', name: 'Grenada', flag: '🇬🇩' },
    { code: 'GE', name: 'Georgia', flag: '🇬🇪' },
    { code: 'GH', name: 'Ghana', flag: '🇬🇭' },
    { code: 'GM', name: 'Gambia', flag: '🇬🇲' },
    { code: 'GN', name: 'Guinea', flag: '🇬🇳' },
    { code: 'GQ', name: 'Equatorial Guinea', flag: '🇬🇶' },
    { code: 'GR', name: 'Greece', flag: '🇬🇷' },
    { code: 'GT', name: 'Guatemala', flag: '🇬🇹' },
    { code: 'GW', name: 'Guinea-Bissau', flag: '🇬🇼' },
    { code: 'GY', name: 'Guyana', flag: '🇬🇾' },
    { code: 'HK', name: 'Hong Kong', flag: '🇭🇰' },
    { code: 'HN', name: 'Honduras', flag: '🇭🇳' },
    { code: 'HR', name: 'Croatia', flag: '🇭🇷' },
    { code: 'HT', name: 'Haiti', flag: '🇭🇹' },
    { code: 'HU', name: 'Hungary', flag: '🇭🇺' },
    { code: 'ID', name: 'Indonesia', flag: '🇮🇩' },
    { code: 'IE', name: 'Ireland', flag: '🇮🇪' },
    { code: 'IL', name: 'Israel', flag: '🇮🇱' },
    { code: 'IN', name: 'India', flag: '🇮🇳' },
    { code: 'IQ', name: 'Iraq', flag: '🇮🇶' },
    { code: 'IR', name: 'Iran', flag: '🇮🇷' },
    { code: 'IS', name: 'Iceland', flag: '🇮🇸' },
    { code: 'IT', name: 'Italy', flag: '🇮🇹' },
    { code: 'JM', name: 'Jamaica', flag: '🇯🇲' },
    { code: 'JO', name: 'Jordan', flag: '🇯🇴' },
    { code: 'JP', name: 'Japan', flag: '🇯🇵' },
    { code: 'KE', name: 'Kenya', flag: '🇰🇪' },
    { code: 'KG', name: 'Kyrgyzstan', flag: '🇰🇬' },
    { code: 'KH', name: 'Cambodia', flag: '🇰🇭' },
    { code: 'KI', name: 'Kiribati', flag: '🇰🇮' },
    { code: 'KM', name: 'Comoros', flag: '🇰🇲' },
    { code: 'KN', name: 'Saint Kitts and Nevis', flag: '🇰🇳' },
    { code: 'KP', name: 'North Korea', flag: '🇰🇵' },
    { code: 'KR', name: 'South Korea', flag: '🇰🇷' },
    { code: 'KW', name: 'Kuwait', flag: '🇰🇼' },
    { code: 'KZ', name: 'Kazakhstan', flag: '🇰🇿' },
    { code: 'LA', name: 'Laos', flag: '🇱🇦' },
    { code: 'LB', name: 'Lebanon', flag: '🇱🇧' },
    { code: 'LC', name: 'Saint Lucia', flag: '🇱🇨' },
    { code: 'LI', name: 'Liechtenstein', flag: '🇱🇮' },
    { code: 'LK', name: 'Sri Lanka', flag: '🇱🇰' },
    { code: 'LR', name: 'Liberia', flag: '🇱🇷' },
    { code: 'LS', name: 'Lesotho', flag: '🇱🇸' },
    { code: 'LT', name: 'Lithuania', flag: '🇱🇹' },
    { code: 'LU', name: 'Luxembourg', flag: '🇱🇺' },
    { code: 'LV', name: 'Latvia', flag: '🇱🇻' },
    { code: 'LY', name: 'Libya', flag: '🇱🇾' },
    { code: 'MA', name: 'Morocco', flag: '🇲🇦' },
    { code: 'MC', name: 'Monaco', flag: '🇲🇨' },
    { code: 'MD', name: 'Moldova', flag: '🇲🇩' },
    { code: 'ME', name: 'Montenegro', flag: '🇲🇪' },
    { code: 'MG', name: 'Madagascar', flag: '🇲🇬' },
    { code: 'MH', name: 'Marshall Islands', flag: '🇲🇭' },
    { code: 'MK', name: 'North Macedonia', flag: '🇲🇰' },
    { code: 'ML', name: 'Mali', flag: '🇲🇱' },
    { code: 'MM', name: 'Myanmar', flag: '🇲🇲' },
    { code: 'MN', name: 'Mongolia', flag: '🇲🇳' },
    { code: 'MR', name: 'Mauritania', flag: '🇲🇷' },
    { code: 'MT', name: 'Malta', flag: '🇲🇹' },
    { code: 'MU', name: 'Mauritius', flag: '🇲🇺' },
    { code: 'MV', name: 'Maldives', flag: '🇲🇻' },
    { code: 'MW', name: 'Malawi', flag: '🇲🇼' },
    { code: 'MX', name: 'Mexico', flag: '🇲🇽' },
    { code: 'MY', name: 'Malaysia', flag: '🇲🇾' },
    { code: 'MZ', name: 'Mozambique', flag: '🇲🇿' },
    { code: 'NA', name: 'Namibia', flag: '🇳🇦' },
    { code: 'NE', name: 'Niger', flag: '🇳🇪' },
    { code: 'NG', name: 'Nigeria', flag: '🇳🇬' },
    { code: 'NI', name: 'Nicaragua', flag: '🇳🇮' },
    { code: 'NL', name: 'Netherlands', flag: '🇳🇱' },
    { code: 'NO', name: 'Norway', flag: '🇳🇴' },
    { code: 'NP', name: 'Nepal', flag: '🇳🇵' },
    { code: 'NR', name: 'Nauru', flag: '🇳🇷' },
    { code: 'NZ', name: 'New Zealand', flag: '🇳🇿' },
    { code: 'OM', name: 'Oman', flag: '🇴🇲' },
    { code: 'PA', name: 'Panama', flag: '🇵🇦' },
    { code: 'PE', name: 'Peru', flag: '🇵🇪' },
    { code: 'PG', name: 'Papua New Guinea', flag: '🇵🇬' },
    { code: 'PH', name: 'Philippines', flag: '🇵🇭' },
    { code: 'PK', name: 'Pakistan', flag: '🇵🇰' },
    { code: 'PL', name: 'Poland', flag: '🇵🇱' },
    { code: 'PT', name: 'Portugal', flag: '🇵🇹' },
    { code: 'PW', name: 'Palau', flag: '🇵🇼' },
    { code: 'PY', name: 'Paraguay', flag: '🇵🇾' },
    { code: 'QA', name: 'Qatar', flag: '🇶🇦' },
    { code: 'RO', name: 'Romania', flag: '🇷🇴' },
    { code: 'RS', name: 'Serbia', flag: '🇷🇸' },
    { code: 'RU', name: 'Russia', flag: '🇷🇺' },
    { code: 'RW', name: 'Rwanda', flag: '🇷🇼' },
    { code: 'SA', name: 'Saudi Arabia', flag: '🇸🇦' },
    { code: 'SB', name: 'Solomon Islands', flag: '🇸🇧' },
    { code: 'SC', name: 'Seychelles', flag: '🇸🇨' },
    { code: 'SD', name: 'Sudan', flag: '🇸🇩' },
    { code: 'SE', name: 'Sweden', flag: '🇸🇪' },
    { code: 'SG', name: 'Singapore', flag: '🇸🇬' },
    { code: 'SI', name: 'Slovenia', flag: '🇸🇮' },
    { code: 'SK', name: 'Slovakia', flag: '🇸🇰' },
    { code: 'SL', name: 'Sierra Leone', flag: '🇸🇱' },
    { code: 'SM', name: 'San Marino', flag: '🇸🇲' },
    { code: 'SN', name: 'Senegal', flag: '🇸🇳' },
    { code: 'SO', name: 'Somalia', flag: '🇸🇴' },
    { code: 'SR', name: 'Suriname', flag: '🇸🇷' },
    { code: 'SS', name: 'South Sudan', flag: '🇸🇸' },
    { code: 'ST', name: 'São Tomé and Príncipe', flag: '🇸🇹' },
    { code: 'SV', name: 'El Salvador', flag: '🇸🇻' },
    { code: 'SY', name: 'Syria', flag: '🇸🇾' },
    { code: 'SZ', name: 'Eswatini', flag: '🇸🇿' },
    { code: 'TD', name: 'Chad', flag: '🇹🇩' },
    { code: 'TG', name: 'Togo', flag: '🇹🇬' },
    { code: 'TH', name: 'Thailand', flag: '🇹🇭' },
    { code: 'TJ', name: 'Tajikistan', flag: '🇹🇯' },
    { code: 'TL', name: 'Timor-Leste', flag: '🇹🇱' },
    { code: 'TM', name: 'Turkmenistan', flag: '🇹🇲' },
    { code: 'TN', name: 'Tunisia', flag: '🇹🇳' },
    { code: 'TO', name: 'Tonga', flag: '🇹🇴' },
    { code: 'TR', name: 'Turkey', flag: '🇹🇷' },
    { code: 'TT', name: 'Trinidad and Tobago', flag: '🇹🇹' },
    { code: 'TV', name: 'Tuvalu', flag: '🇹🇻' },
    { code: 'TW', name: 'Taiwan', flag: '🇹🇼' },
    { code: 'TZ', name: 'Tanzania', flag: '🇹🇿' },
    { code: 'UA', name: 'Ukraine', flag: '🇺🇦' },
    { code: 'UG', name: 'Uganda', flag: '🇺🇬' },
    { code: 'US', name: 'United States', flag: '🇺🇸' },
    { code: 'UY', name: 'Uruguay', flag: '🇺🇾' },
    { code: 'UZ', name: 'Uzbekistan', flag: '🇺🇿' },
    { code: 'VA', name: 'Vatican City', flag: '🇻🇦' },
    { code: 'VC', name: 'Saint Vincent and the Grenadines', flag: '🇻🇨' },
    { code: 'VE', name: 'Venezuela', flag: '🇻🇪' },
    { code: 'VN', name: 'Vietnam', flag: '🇻🇳' },
    { code: 'VU', name: 'Vanuatu', flag: '🇻🇺' },
    { code: 'WS', name: 'Samoa', flag: '🇼🇸' },
    { code: 'YE', name: 'Yemen', flag: '🇾🇪' },
    { code: 'ZA', name: 'South Africa', flag: '🇿🇦' },
    { code: 'ZM', name: 'Zambia', flag: '🇿🇲' },
    { code: 'ZW', name: 'Zimbabwe', flag: '🇿🇼' }
];

// Country search functionality
function initCountrySearch(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    // Create search wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'country-search-wrapper position-relative';
    
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'form-control';
    searchInput.placeholder = '🔍 Search countries...';
    
    const dropdown = document.createElement('div');
    dropdown.className = 'country-dropdown position-absolute w-100 bg-white border rounded shadow-sm';
    dropdown.style.cssText = 'max-height: 200px; overflow-y: auto; z-index: 1000; display: none; top: 100%;';
    
    wrapper.appendChild(searchInput);
    wrapper.appendChild(dropdown);
    select.parentNode.insertBefore(wrapper, select);
    select.style.display = 'none';
    
    let isOpen = false;
    
    function renderCountries(countries) {
        dropdown.innerHTML = '';
        countries.slice(0, 50).forEach(country => {
            const item = document.createElement('div');
            item.className = 'px-3 py-2 cursor-pointer border-bottom';
            item.innerHTML = `${country.flag} ${country.name}`;
            item.style.cursor = 'pointer';
            
            item.addEventListener('mouseenter', () => item.style.backgroundColor = '#f8f9fa');
            item.addEventListener('mouseleave', () => item.style.backgroundColor = '');
            item.addEventListener('click', () => {
                select.value = country.code;
                searchInput.value = `${country.flag} ${country.name}`;
                dropdown.style.display = 'none';
                isOpen = false;
                select.dispatchEvent(new Event('change'));
            });
            
            dropdown.appendChild(item);
        });
    }
    
    searchInput.addEventListener('focus', () => {
        if (!isOpen) {
            renderCountries(COUNTRIES);
            dropdown.style.display = 'block';
            isOpen = true;
        }
    });
    
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = COUNTRIES.filter(c => 
            c.name.toLowerCase().includes(query) || c.code.toLowerCase().includes(query)
        );
        renderCountries(filtered);
    });
    
    document.addEventListener('click', (e) => {
        if (!wrapper.contains(e.target)) {
            dropdown.style.display = 'none';
            isOpen = false;
        }
    });
    
    // Set initial value if exists
    const currentValue = select.value;
    if (currentValue) {
        const country = COUNTRIES.find(c => c.code === currentValue);
        if (country) {
            searchInput.value = `${country.flag} ${country.name}`;
        }
    }
}