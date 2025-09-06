import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import json

# Configure Gemini API
genai.configure(api_key="AIzaSyB6ncuqZqLvyN8ULJSZUWgNck9rUKWiPG4")
model = genai.GenerativeModel('gemini-pro')

# Standard material rates based on DSR (example rates - update as per current DSR)
MATERIAL_RATES = {
    "cement": {"rate": 400, "unit": "per bag"},
    "steel": {"rate": 65000, "unit": "per MT"},
    "bricks": {"rate": 7000, "unit": "per 1000 nos"},
    "sand": {"rate": 1500, "unit": "per cum"},
    "aggregate_20mm": {"rate": 1200, "unit": "per cum"},
    "aggregate_10mm": {"rate": 1300, "unit": "per cum"},
}

# Standard material coefficients for different construction types
CONSTRUCTION_COEFFICIENTS = {
    "RCC Slab (4 inch)": {
        "cement": 4.5,  # bags per 100 sqft
        "steel": 0.08,  # MT per 100 sqft
        "sand": 0.25,   # cum per 100 sqft
        "aggregate_20mm": 0.5,  # cum per 100 sqft
    },
    "Brick Wall (9 inch)": {
        "cement": 3.0,  # bags per 100 sqft
        "bricks": 1350,  # per 100 sqft
        "sand": 0.35,   # cum per 100 sqft
    },
    "Plaster (12mm)": {
        "cement": 1.5,  # bags per 100 sqft
        "sand": 0.15,   # cum per 100 sqft
    },
    "Flooring (IPS)": {
        "cement": 2.0,  # bags per 100 sqft
        "sand": 0.18,   # cum per 100 sqft
        "aggregate_10mm": 0.15,  # cum per 100 sqft
    }
}

def calculate_materials(length, width, construction_type):
    """Calculate material requirements based on area and construction type"""
    area = length * width
    area_in_100sqft = area / 100
    
    materials = {}
    coefficients = CONSTRUCTION_COEFFICIENTS.get(construction_type, {})
    
    for material, quantity_per_100sqft in coefficients.items():
        materials[material] = quantity_per_100sqft * area_in_100sqft
    
    return materials, area

def calculate_cost(materials):
    """Calculate cost for each material and total"""
    cost_breakdown = {}
    total_cost = 0
    
    for material, quantity in materials.items():
        if material in MATERIAL_RATES:
            rate = MATERIAL_RATES[material]["rate"]
            cost = quantity * rate
            cost_breakdown[material] = {
                "quantity": round(quantity, 2),
                "rate": rate,
                "unit": MATERIAL_RATES[material]["unit"],
                "cost": round(cost, 2)
            }
            total_cost += cost
    
    return cost_breakdown, total_cost

def get_ai_suggestions(area, construction_type, budget):
    """Get AI-powered suggestions for optimization"""
    try:
        prompt = f"""
        For a construction project with following details:
        - Area: {area} sqft
        - Construction Type: {construction_type}
        - Budget: ₹{budget:,.2f}
        
        Provide brief suggestions for:
        1. Cost optimization tips
        2. Material quality recommendations
        3. Common mistakes to avoid
        
        Keep the response concise and practical.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI suggestions unavailable: {str(e)}"

# Streamlit UI
st.set_page_config(page_title="Construction Calculator - DSR Based", layout="wide")

st.title("🏗️ Construction Material Calculator")
st.caption("Based on PWD/CPWD DSR Standards for Indian Construction")

# Sidebar for inputs
with st.sidebar:
    st.header("Project Details")
    
    # Dimension inputs
    col1, col2 = st.columns(2)
    with col1:
        length = st.number_input("Length (ft)", min_value=1.0, value=17.0, step=0.5)
    with col2:
        width = st.number_input("Width (ft)", min_value=1.0, value=70.0, step=0.5)
    
    # Construction type selection
    construction_type = st.selectbox(
        "Select Construction Type",
        options=list(CONSTRUCTION_COEFFICIENTS.keys())
    )
    
    # Additional options
    st.subheader("Additional Options")
    include_labor = st.checkbox("Include Labor Costs", value=True)
    wastage_factor = st.slider("Wastage Factor (%)", 0, 20, 5)
    
    calculate_btn = st.button("Calculate", type="primary", use_container_width=True)

# Main content area
if calculate_btn:
    # Calculate materials
    materials, area = calculate_materials(length, width, construction_type)
    
    # Apply wastage factor
    materials = {k: v * (1 + wastage_factor/100) for k, v in materials.items()}
    
    # Calculate costs
    cost_breakdown, material_cost = calculate_cost(materials)
    
    # Calculate labor cost (approximate 30% of material cost)
    labor_cost = material_cost * 0.3 if include_labor else 0
    total_cost = material_cost + labor_cost
    
    # Display results
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Area", f"{area:,.0f} sqft")
    with col2:
        st.metric("Material Cost", f"₹{material_cost:,.2f}")
    with col3:
        st.metric("Total Cost", f"₹{total_cost:,.2f}")
    
    # Material breakdown
    st.subheader("📊 Material Breakdown")
    
    # Create DataFrame for materials
    material_data = []
    for material, details in cost_breakdown.items():
        material_data.append({
            "Material": material.replace("_", " ").title(),
            "Quantity": f"{details['quantity']:.2f}",
            "Unit": details['unit'],
            "Rate": f"₹{details['rate']:,}",
            "Cost": f"₹{details['cost']:,.2f}"
        })
    
    df = pd.DataFrame(material_data)
    st.dataframe(df, use_container_width=True)
    
    # Cost distribution chart
    st.subheader("💰 Cost Distribution")
    
    # Prepare data for pie chart
    chart_data = pd.DataFrame({
        'Material': [item['Material'] for item in material_data],
        'Cost': [cost_breakdown[m]['cost'] for m in cost_breakdown.keys()]
    })
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.bar_chart(chart_data.set_index('Material'))
    
    with col2:
        st.subheader("Summary")
        st.write(f"**Construction Type:** {construction_type}")
        st.write(f"**Area:** {area:,.0f} sqft")
        st.write(f"**Material Cost:** ₹{material_cost:,.2f}")
        if include_labor:
            st.write(f"**Labor Cost:** ₹{labor_cost:,.2f}")
        st.write(f"**Total Cost:** ₹{total_cost:,.2f}")
        st.write(f"**Cost per sqft:** ₹{total_cost/area:.2f}")
    
    # AI Suggestions
    with st.expander("🤖 AI-Powered Suggestions", expanded=True):
        with st.spinner("Getting AI recommendations..."):
            suggestions = get_ai_suggestions(area, construction_type, total_cost)
            st.markdown(suggestions)
    
    # Download report
    st.subheader("📥 Download Report")
    
    # Create report content
    report_content = {
        "project_details": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "dimensions": f"{length} x {width} ft",
            "area": area,
            "construction_type": construction_type
        },
        "materials": material_data,
        "costs": {
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "total_cost": total_cost,
            "cost_per_sqft": total_cost/area
        }
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON download
        json_string = json.dumps(report_content, indent=2)
        st.download_button(
            label="Download JSON Report",
            data=json_string,
            file_name=f"construction_estimate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # CSV download
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV Report",
            data=csv,
            file_name=f"material_breakdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# Information section
with st.expander("ℹ️ About DSR Rates"):
    st.write("""
    This calculator uses standard rates based on Delhi Schedule of Rates (DSR) / CPWD rates.
    
    **Note:**
    - Rates are indicative and may vary based on location and market conditions
    - Always verify current rates from official DSR publications
    - Labor costs are estimated at 30% of material costs
    - Wastage factor accounts for material handling and cutting losses
    
    **Material Units:**
    - Cement: Bags (50 kg each)
    - Steel: Metric Tons (MT)
    - Bricks: Numbers (in thousands)
    - Sand/Aggregate: Cubic meters (cum)
    """)

# Footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit and Google Gemini AI | Rates based on DSR standards")
